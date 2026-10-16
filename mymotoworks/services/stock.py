"""Stock use cases: adjust the stock of items, list the changes, recount."""

import math

from mymotoworks.domain.stock import clean_adjustment, clean_count
from mymotoworks.errors import NotFoundError, ValidationError
from mymotoworks.repositories import ItemRepository, StockRepository
from mymotoworks.services.base import Service
from mymotoworks.services.presenters import batch_json, history_json


class StockService(Service):
    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.items = ItemRepository(db)
        self.stock = StockRepository(db)

    def _json(self, batch):
        return batch_json(batch, self.stock.batch_adjustments(batch["id"]))

    def _counted_item(self, item_id):
        """The item, or a ValidationError when it does not exist or does not count stock."""
        item = self.items.get(item_id)
        if item is None:
            raise ValidationError("An item in the list does not exist.")
        if not item["track_stock"]:
            raise ValidationError(f"{item['name']} does not count stock.")
        return item

    def adjust(self, data):
        """Change the stock of one or more items by a number, all or nothing. Returns {"batch",
        "duplicate"}; duplicate is True when this save (same client_ref) was already done, and
        nothing is changed twice."""
        request = clean_adjustment(data)
        if request["client_ref"]:
            saved = self.stock.find_batch_by_ref(self.user["id"], request["client_ref"])
            if saved:
                return {"batch": self._json(saved), "duplicate": True}

        # Check every line first, so a bad line saves nothing and changes no stock.
        checked = [(self._counted_item(line["item_id"]), line["change"]) for line in request["lines"]]
        batch_id = self.stock.create_batch(self.user["id"], "adjustment", request["reason"], request["note"],
                                           request["client_ref"])
        for item, change in checked:
            self.stock.add_adjustment(batch_id, item, change, item["stock"], item["stock"] + change)
            self.items.change_stock(item["id"], change)
        self.commit()
        return {"batch": self._json(self.stock.get_batch(batch_id)), "duplicate": False}

    DEFAULT_PER_PAGE = 20
    MAX_PER_PAGE = 50

    def list(self, item_id=None, page=1, per_page=DEFAULT_PER_PAGE):
        """One page of stock changes, newest first, for all items or for one."""
        item = None
        if item_id is not None:
            row = self.items.get(item_id)
            if row is None:
                raise NotFoundError("Item not found.")
            item = {"id": row["id"], "name": row["name"], "stock": row["stock"]}
        per_page = max(1, min(per_page, self.MAX_PER_PAGE))
        total = self.stock.count_adjustments(item_id)
        pages = max(1, math.ceil(total / per_page))
        page = max(1, page)
        rows = self.stock.page_adjustments(item_id, per_page, (page - 1) * per_page)
        return {"adjustments": [history_json(row) for row in rows], "page": page, "pages": pages,
                "total": total, "item": item}

    def count(self, data):
        """Set the stock of the counted items to what was counted. Items whose count already equals their
        stock make no record, and a recount where nothing changed makes no batch at all. The change is
        worked out from the stock at the moment of saving, so a sale approved while the owner was counting
        does not spoil the result: the stock ends at the counted number."""
        request = clean_count(data)
        if request["client_ref"]:
            saved = self.stock.find_batch_by_ref(self.user["id"], request["client_ref"])
            if saved:
                batch = self._json(saved)
                return {"batch": batch, "changed": len(batch["adjustments"]), "unchanged": None, "duplicate": True}

        # Check every line first, so a bad line saves nothing and changes no stock.
        checked = [(self._counted_item(line["item_id"]), line["counted"]) for line in request["lines"]]
        changes = [(item, counted - item["stock"]) for item, counted in checked if counted != item["stock"]]
        unchanged = len(checked) - len(changes)
        if not changes:
            return {"batch": None, "changed": 0, "unchanged": unchanged, "duplicate": False}
        batch_id = self.stock.create_batch(self.user["id"], "recount", "count_correction", request["note"],
                                           request["client_ref"])
        for item, change in changes:
            self.stock.add_adjustment(batch_id, item, change, item["stock"], item["stock"] + change)
            self.items.change_stock(item["id"], change)
        self.commit()
        return {"batch": self._json(self.stock.get_batch(batch_id)), "changed": len(changes),
                "unchanged": unchanged, "duplicate": False}
