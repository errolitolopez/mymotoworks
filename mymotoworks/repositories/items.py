"""SQL for the items table. It never commits: the service does."""

from mymotoworks.repositories.base import Repository


class ItemRepository(Repository):
    def get(self, item_id):
        return self.one("SELECT * FROM items WHERE id = ?", (item_id,))

    def create(self, fields):
        """Add an item (fields from domain.items.clean_item with creating=True) and return its id."""
        cursor = self.execute(
            "INSERT INTO items (name, model, part_no, puhunan, benta, stock, reorder_level, track_stock, active) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (fields["name"], fields["model"], fields["part_no"], fields["puhunan"], fields["benta"],
             fields["stock"], fields["reorder_level"], int(fields["track_stock"]), int(fields["active"])),
        )
        return cursor.lastrowid

    def list_all(self, include_inactive=False):
        """Every item by name, then model. Feature B replaces this with a searched, paged list."""
        where = "" if include_inactive else "WHERE active = 1"
        return self.all(f"SELECT * FROM items {where} ORDER BY name COLLATE NOCASE, model COLLATE NOCASE, id")
