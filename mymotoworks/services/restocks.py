"""Restock use cases: record a restock, list the history, void one."""

import math

from mymotoworks import config
from mymotoworks.domain.restocks import clean_restock, clean_restock_void_reason
from mymotoworks.errors import NotFoundError, ValidationError
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

    DEFAULT_PER_PAGE = 20
    MAX_PER_PAGE = 50

    def list(self, page=1, per_page=DEFAULT_PER_PAGE):
        """One page of the history, newest first, with each restock's lines."""
        per_page = max(1, min(per_page, self.MAX_PER_PAGE))
        total = self.restocks.count()
        pages = max(1, math.ceil(total / per_page))
        page = max(1, page)
        rows = self.restocks.page(per_page, (page - 1) * per_page)
        return {"restocks": [self._json(row) for row in rows], "page": page, "pages": pages, "total": total}

    def void(self, restock_id, data):
        """Cancel a restock: its quantities come out of the stock again, and each item's old cost is put
        back unless the cost was changed since (another restock, or an edit). The record stays."""
        restock = self.restocks.get(restock_id)
        if restock is None:
            raise NotFoundError("Restock not found.")
        if restock["voided_at"] is not None:
            raise ValidationError("This restock is already voided.")
        reason = clean_restock_void_reason(data.get("reason"))
        for line in self.restocks.lines(restock_id):
            self.items.change_stock(line["item_id"], -line["qty"])
            item = self.items.get(line["item_id"])
            # Only when the cost is still the one this restock set: otherwise a later change would be lost.
            if item["puhunan"] == line["puhunan"]:
                self.items.set_puhunan(line["item_id"], line["old_puhunan"])
        self.restocks.mark_voided(restock_id, self.user["id"], reason)
        self.commit()
        return {"restock": self._json(self.restocks.get(restock_id))}
