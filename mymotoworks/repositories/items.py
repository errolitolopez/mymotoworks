"""SQL for the items table. It never commits: the service does."""

from mymotoworks.domain.text import like_pattern
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

    @staticmethod
    def _where(words, low, include_inactive):
        """The WHERE part and its parameters. Every word must be in the name, model or part no."""
        conditions, params = [], []
        if not include_inactive:
            conditions.append("active = 1")
        if low:
            # Untracked items (services) have no count, so they are never low.
            conditions.append("track_stock = 1 AND stock <= reorder_level")
        for word in words:
            pattern = like_pattern(word)
            conditions.append("(name LIKE ? ESCAPE '\\' OR model LIKE ? ESCAPE '\\' OR part_no LIKE ? ESCAPE '\\')")
            params += [pattern, pattern, pattern]
        return ("WHERE " + " AND ".join(conditions)) if conditions else "", params

    def count(self, words=(), low=False, include_inactive=False):
        where, params = self._where(words, low, include_inactive)
        return self.value(f"SELECT COUNT(*) FROM items {where}", params)

    def search(self, words=(), low=False, include_inactive=False, limit=50, offset=0):
        """One page of items by name, then model."""
        where, params = self._where(words, low, include_inactive)
        return self.all(
            f"SELECT * FROM items {where} ORDER BY name COLLATE NOCASE, model COLLATE NOCASE, id LIMIT ? OFFSET ?",
            params + [limit, offset],
        )
