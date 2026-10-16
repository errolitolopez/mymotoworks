"""Item use cases: list, add, change."""

from mymotoworks.domain.items import clean_item
from mymotoworks.repositories import ItemRepository
from mymotoworks.services.base import Service
from mymotoworks.services.presenters import item_json


class ItemService(Service):
    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.items = ItemRepository(db)

    def list(self, inactive=False):
        """Items for the page. Only the admin may ask for deactivated ones."""
        include_inactive = inactive and self.user["role"] == "admin"
        rows = self.items.list_all(include_inactive)
        return {"items": [item_json(row, self.user["role"]) for row in rows]}

    def create(self, data):
        """Add an item. Returns its JSON."""
        item_id = self.items.create(clean_item(data, creating=True))
        self.commit()
        return item_json(self.items.get(item_id), self.user["role"])
