"""Sale use cases: record a sale, list a day, void a sale."""

from mymotoworks import config
from mymotoworks.domain.sales import clean_date, clean_sale, clean_void_reason
from mymotoworks.errors import ForbiddenError, NotFoundError, ValidationError
from mymotoworks.repositories import ItemRepository, SaleRepository
from mymotoworks.services.base import Service
from mymotoworks.services.presenters import sale_json


class SaleService(Service):
    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.items = ItemRepository(db)
        self.sales = SaleRepository(db)

    def _json(self, sale):
        return sale_json(sale, self.sales.lines(sale["id"]), self.user["role"])

    def create(self, data):
        """Save a sale, all or nothing. Returns {"sale", "duplicate"}: duplicate is True when this
        cart (same client_ref) was already saved, and nothing is saved twice."""
        request = clean_sale(data, config.shop_today(), self.user["role"] == "admin")
        if request["client_ref"]:
            saved = self.sales.find_by_ref(self.user["id"], request["client_ref"])
            if saved:
                return {"sale": self._json(saved), "duplicate": True}

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

        sale_id = self.sales.create(request["sale_date"], self.user["id"], total, request["client_ref"])
        for item, qty, benta in priced:
            self.sales.add_line(sale_id, item, qty, benta)
            if item["track_stock"]:
                self.items.change_stock(item["id"], -qty)
        self.commit()
        return {"sale": self._json(self.sales.get(sale_id)), "duplicate": False}

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
        reason = clean_void_reason(data.get("reason"))
        for line in self.sales.lines(sale_id):
            # `tracked` says whether this line took stock when it was sold. Using it, not the item's
            # current setting, puts back exactly what was taken.
            if line["tracked"]:
                self.items.change_stock(line["item_id"], line["qty"])
        self.sales.mark_voided(sale_id, self.user["id"], reason)
        self.commit()
        return {"sale": self._json(self.sales.get(sale_id))}
