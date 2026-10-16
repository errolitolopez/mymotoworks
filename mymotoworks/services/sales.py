"""Sale use cases: record a sale, list a day, void a sale."""

from mymotoworks import config
from mymotoworks.domain.sales import clean_sale
from mymotoworks.errors import ValidationError
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
