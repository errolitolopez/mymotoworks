"""Restock use cases: record a restock, list the history, void one."""

from mymotoworks import config
from mymotoworks.domain.restocks import clean_restock
from mymotoworks.errors import ValidationError
from mymotoworks.repositories import ItemRepository, RestockRepository
from mymotoworks.services.base import Service
from mymotoworks.services.presenters import restock_json


class RestockService(Service):
    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.items = ItemRepository(db)
        self.restocks = RestockRepository(db)

    def _json(self, restock):
        return restock_json(restock, self.restocks.lines(restock["id"]))

    def create(self, data):
        """Save a restock, all or nothing: every item's stock goes up and its cost becomes the new
        cost. Returns {"restock", "duplicate"}; duplicate is True when this restock (same client_ref)
        was already saved, and nothing is saved twice."""
        request = clean_restock(data, config.shop_today())
        if request["client_ref"]:
            saved = self.restocks.find_by_ref(self.user["id"], request["client_ref"])
            if saved:
                return {"restock": self._json(saved), "duplicate": True}

        # Check every line first, so a bad line saves nothing and changes nothing.
        priced = []
        total = 0
        for line in request["lines"]:
            item = self.items.get(line["item_id"])
            if item is None:
                raise ValidationError("An item in the list does not exist.")
            if not item["active"]:
                raise ValidationError(f"{item['name']} is no longer for sale.")
            if not item["track_stock"]:
                raise ValidationError(f"{item['name']} does not count stock, so it cannot be restocked.")
            puhunan = item["puhunan"] if line["puhunan"] is None else line["puhunan"]
            priced.append((item, line["qty"], puhunan))
            total += line["qty"] * puhunan

        restock_id = self.restocks.create(request["restock_date"], self.user["id"], total, request["note"],
                                          request["client_ref"])
        for item, qty, puhunan in priced:
            self.restocks.add_line(restock_id, item, qty, puhunan)
            self.items.change_stock(item["id"], qty)
            self.items.set_puhunan(item["id"], puhunan)
        self.commit()
        return {"restock": self._json(self.restocks.get(restock_id)), "duplicate": False}
