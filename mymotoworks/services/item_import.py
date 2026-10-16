"""The one-time import of items: build the plan, and write it."""

from mymotoworks.domain.item_import import build_plan
from mymotoworks.repositories import ItemRepository
from mymotoworks.services.base import Service


class ItemImportService(Service):
    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.items = ItemRepository(db)

    def plan(self, rows):
        """What the import would do with these spreadsheet rows. Saves nothing."""
        plan = build_plan(rows)
        # Deactivated items count too: the import is only for a shop with no items at all.
        plan.existing = self.items.count(include_inactive=True)
        return plan
