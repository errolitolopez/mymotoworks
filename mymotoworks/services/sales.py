"""Sale use cases: record a sale, list a day, void a sale."""

from mymotoworks import config
from mymotoworks.domain.sales import clean_date, clean_sale, clean_void_reason
from mymotoworks.errors import ForbiddenError, NotFoundError, ValidationError
from mymotoworks.repositories import ItemRepository, SaleRepository
from mymotoworks.services.base import Service
from mymotoworks.services.presenters import item_json, sale_json


class SaleService(Service):
    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.items = ItemRepository(db)
        self.sales = SaleRepository(db)

    def _json(self, sale):
        return sale_json(sale, self.sales.lines(sale["id"]), self.user["role"])

    def create(self, data):
        """Save a sale, all or nothing. Returns {"sale", "duplicate"}: duplicate is True when this
        cart (same client_ref) was already saved, and nothing is saved twice. With `replaces` (admin
        only) the earlier sale is voided in the same step; it stays in the list as history."""
        request = clean_sale(data, config.shop_today(), self.user["role"] == "admin")
        if request["replaces"] is not None and self.user["role"] != "admin":
            raise ForbiddenError("Only the admin can replace a sale.")
        if request["client_ref"]:
            saved = self.sales.find_by_ref(self.user["id"], request["client_ref"])
            if saved:
                return {"sale": self._json(saved), "duplicate": True}

        old = None
        if request["replaces"] is not None:
            old = self.sales.get(request["replaces"])
            if old is None:
                raise NotFoundError("Sale not found.")
            if old["voided_at"] is not None:
                raise ValidationError("That sale is already voided.")
            # The correction counts on the day of the sale it corrects, so the day's totals stay right.
            request["sale_date"] = old["sale_date"]

        # Check every line first, so a bad line saves nothing and changes no stock.
        priced = []
        total = 0
        for line in request["lines"]:
            item = self.items.get(line["item_id"])
            if item is None:
                raise ValidationError("An item in the cart does not exist.")
            if not item["active"]:
                raise ValidationError(f"{item['name']} is no longer for sale.")
            benta = item["benta"] if line["benta"] is None else line["benta"]
            priced.append((item, line["qty"], benta))
            total += line["qty"] * benta

        # Every sale, the admin's too, waits for approval and does not touch the stock until the admin
        # approves it.
        sale_id = self.sales.create(request["sale_date"], self.user["id"], total, request["client_ref"],
                                    request["note"], old["id"] if old else None)
        for item, qty, benta in priced:
            self.sales.add_line(sale_id, item, qty, benta)
        if old:
            self._cancel(old, f"Replaced by sale #{sale_id}")
        self.commit()
        return {"sale": self._json(self.sales.get(sale_id)), "duplicate": False}

    def _cancel(self, sale, reason):
        """Void a sale (no commit): put back the stock its lines took and mark it voided. A sale that
        was never approved took no stock, so none is put back."""
        if sale["approved_at"] is not None:
            for line in self.sales.lines(sale["id"]):
                # `tracked` says whether this line takes stock. Using it, not the item's current
                # setting, puts back exactly what was taken.
                if line["tracked"]:
                    self.items.change_stock(line["item_id"], line["qty"])
        self.sales.mark_voided(sale["id"], self.user["id"], reason)

    def _approve(self, sale):
        """Approve a sale (no commit): its lines take their stock now. Stock may go below 0."""
        for line in self.sales.lines(sale["id"]):
            if line["tracked"]:
                self.items.change_stock(line["item_id"], -line["qty"])
        self.sales.mark_approved(sale["id"], self.user["id"])

    def approve(self, sale_id):
        """The admin approves a pending sale. Returns its JSON."""
        sale = self.sales.get(sale_id)
        if sale is None:
            raise NotFoundError("Sale not found.")
        if sale["voided_at"] is not None:
            raise ValidationError("This sale was voided.")
        if sale["approved_at"] is not None:
            raise ValidationError("This sale is already approved.")
        self._approve(sale)
        self.commit()
        return {"sale": self._json(self.sales.get(sale_id))}

    def approve_all(self, date_text=None):
        """The admin approves every pending sale of one day in one step (today when no date)."""
        day = config.shop_today() if date_text in (None, "") else clean_date(date_text)
        approved = 0
        for sale_id in self.sales.pending_ids(day.isoformat()):
            self._approve(self.sales.get(sale_id))
            approved += 1
        self.commit()
        return {"approved": approved, "date": day.isoformat()}

    def pending_overview(self):
        """{"count", "oldest_date"} of the sales waiting for approval, for the admin's Home page."""
        return self.sales.pending_overview()

    def copy_data(self, sale_id):
        """What the Sell page needs to start a new cart from this sale: its lines with the price that
        was charged, the note and the date. Saves nothing. Staff may only copy today's sales."""
        sale = self.sales.get(sale_id)
        if sale is None:
            raise NotFoundError("Sale not found.")
        if sale["sale_date"] != config.shop_today().isoformat() and self.user["role"] != "admin":
            raise ForbiddenError("You can only see today's sales.")
        lines, skipped = [], []
        for line in self.sales.lines(sale_id):
            item = self.items.get(line["item_id"])
            if item is None or not item["active"]:
                skipped.append(f"{line['item_name']} is no longer for sale.")
                continue
            lines.append({"item": item_json(item, self.user["role"]), "qty": line["qty"], "benta": line["benta"]})
        return {"sale_id": sale["id"], "sale_date": sale["sale_date"], "note": sale["note"],
                "voided": sale["voided_at"] is not None, "lines": lines, "skipped": skipped}

    def list_day(self, date_text=None):
        """The sales of one day with the day's totals. Staff may only ask for today. Tubo is only
        in the answer for the admin."""
        today = config.shop_today()
        day = today if date_text in (None, "") else clean_date(date_text)
        if day != today and self.user["role"] != "admin":
            raise ForbiddenError("You can only see today's sales.")
        totals = self.sales.day_totals(day.isoformat())
        if self.user["role"] != "admin":
            del totals["tubo"]
        return {
            "date": day.isoformat(),
            "sales": [self._json(row) for row in self.sales.list_for_day(day.isoformat())],
            "summary": totals,
        }

    def void(self, sale_id, data):
        """Cancel a sale: its stock comes back and it leaves the totals. Returns its JSON."""
        sale = self.sales.get(sale_id)
        if sale is None:
            raise NotFoundError("Sale not found.")
        if sale["voided_at"] is not None:
            raise ValidationError("This sale is already voided.")
        self._cancel(sale, clean_void_reason(data.get("reason")))
        self.commit()
        return {"sale": self._json(self.sales.get(sale_id))}
