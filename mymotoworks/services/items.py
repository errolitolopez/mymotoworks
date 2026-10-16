"""Item use cases: list, add, change."""

import math

from mymotoworks.domain.items import clean_item
from mymotoworks.domain.text import search_words
from mymotoworks.repositories import ItemRepository
from mymotoworks.services.base import Service
from mymotoworks.services.presenters import item_json


class ItemService(Service):
    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.items = ItemRepository(db)

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

    def create(self, data):
        """Add an item. Returns its JSON."""
        item_id = self.items.create(clean_item(data, creating=True))
        self.commit()
        return item_json(self.items.get(item_id), self.user["role"])
