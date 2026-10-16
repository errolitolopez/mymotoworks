"""Item use cases: list, add, change."""

import math

from mymotoworks.domain.items import clean_item
from mymotoworks.domain.text import search_words
from mymotoworks.errors import NotFoundError
from mymotoworks.repositories import ItemRepository
from mymotoworks.services.base import Service
from mymotoworks.services.presenters import item_json


class ItemService(Service):
    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.items = ItemRepository(db)

    # The shop has a few hundred items. This is a safety limit, so one answer can never grow without end.
    MAX_ALL = 5000
    DEFAULT_PER_PAGE = 50
    MAX_PER_PAGE = 100

    def list(self, query="", low=False, inactive=False, page=1, per_page=DEFAULT_PER_PAGE):
        """One page of items. Only the admin may ask for deactivated ones."""
        include_inactive = inactive and self.user["role"] == "admin"
        words = search_words(query)
        per_page = max(1, min(per_page, self.MAX_PER_PAGE))
        total = self.items.count(words, low, include_inactive)
        pages = max(1, math.ceil(total / per_page))
        page = max(1, page)
        rows = self.items.search(words, low, include_inactive, per_page, (page - 1) * per_page)
        return {
            "items": [item_json(row, self.user["role"]) for row in rows],
            "page": page, "pages": pages, "total": total,
        }

    def list_all_active(self):
        """Every active item in one answer, for the Sell page (it shows the whole list and filters it
        in the page). Cost and profit are left out for staff, as everywhere."""
        rows = self.items.search(limit=self.MAX_ALL)
        return {"items": [item_json(row, self.user["role"]) for row in rows]}

    def create(self, data):
        """Add an item. Returns its JSON."""
        item_id = self.items.create(clean_item(data, creating=True))
        self.commit()
        return item_json(self.items.get(item_id), self.user["role"])

    # What an edit may change. Stock is not here: it moves only through sales, restocks and adjustments.
    EDITABLE = ("name", "model", "part_no", "puhunan", "benta", "reorder_level", "track_stock", "active")

    def update(self, item_id, data):
        """Change an item. Only the keys sent change; the rest stay as saved. Returns its JSON."""
        row = self.items.get(item_id)
        if row is None:
            raise NotFoundError("Item not found.")
        merged = {key: row[key] for key in self.EDITABLE}
        merged.update({key: data[key] for key in self.EDITABLE if key in data})
        self.items.update(item_id, clean_item(merged, creating=False))
        self.commit()
        return item_json(self.items.get(item_id), self.user["role"])
