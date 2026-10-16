"""SQL for the restocks and restock_lines tables. It never commits: the service does."""

from mymotoworks.repositories.base import Repository

# A restock with its recorder's name.
RESTOCK_COLUMNS = "restocks.*, users.name AS user_name"


class RestockRepository(Repository):
    def create(self, restock_date, user_id, total, note, client_ref):
        cursor = self.execute(
            "INSERT INTO restocks (restock_date, user_id, total, note, client_ref) VALUES (?, ?, ?, ?, ?)",
            (restock_date, user_id, total, note, client_ref),
        )
        return cursor.lastrowid

    def add_line(self, restock_id, item, qty, puhunan):
        """One line. The item's name and its cost before this restock are copied now."""
        self.execute(
            "INSERT INTO restock_lines (restock_id, item_id, item_name, qty, puhunan, old_puhunan) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (restock_id, item["id"], item["name"], qty, puhunan, item["puhunan"]),
        )

    def get(self, restock_id):
        return self.one(
            f"SELECT {RESTOCK_COLUMNS} FROM restocks JOIN users ON users.id = restocks.user_id "
            "WHERE restocks.id = ?", (restock_id,))

    def lines(self, restock_id):
        return self.all("SELECT * FROM restock_lines WHERE restock_id = ? ORDER BY id", (restock_id,))

    def find_by_ref(self, user_id, client_ref):
        """The restock this person already saved with this reference, or None."""
        return self.one(
            f"SELECT {RESTOCK_COLUMNS} FROM restocks JOIN users ON users.id = restocks.user_id "
            "WHERE restocks.user_id = ? AND restocks.client_ref = ?", (user_id, client_ref))

    def count(self):
        return self.value("SELECT COUNT(*) FROM restocks")

    def page(self, limit, offset):
        """One page of restocks, newest first, voided ones too."""
        return self.all(
            f"SELECT {RESTOCK_COLUMNS} FROM restocks JOIN users ON users.id = restocks.user_id "
            "ORDER BY restocks.id DESC LIMIT ? OFFSET ?", (limit, offset))

    def mark_voided(self, restock_id, user_id, reason):
        self.execute(
            "UPDATE restocks SET voided_at = CURRENT_TIMESTAMP, voided_by = ?, void_reason = ? WHERE id = ?",
            (user_id, reason, restock_id))
