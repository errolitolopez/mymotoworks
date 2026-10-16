"""The one-time import of items: build the plan, and write it."""

from mymotoworks.domain.item_import import build_plan
from mymotoworks.errors import ValidationError
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

    def run(self, plan):
        """Add every item of the plan, all or nothing. Returns how many were added."""
        if not plan.items:
            raise ValidationError("There is nothing to import.")
        if self.items.count(include_inactive=True) > 0:
            raise ValidationError("The shop already has items. The import is only for a new, empty database.")
        for _, fields in plan.items:
            self.items.create(fields)
        # One commit at the end: an error above leaves nothing saved.
        self.commit()
        return len(plan.items)
