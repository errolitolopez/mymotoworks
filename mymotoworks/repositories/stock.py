"""SQL for the stock_batches and stock_adjustments tables. It never commits: the service does."""

from mymotoworks.repositories.base import Repository

# A batch with who saved it.
BATCH_COLUMNS = "stock_batches.*, users.name AS user_name"


class StockRepository(Repository):
    def create_batch(self, user_id, kind, reason, note, client_ref):
        cursor = self.execute(
            "INSERT INTO stock_batches (user_id, kind, reason, note, client_ref) VALUES (?, ?, ?, ?, ?)",
            (user_id, kind, reason, note, client_ref),
        )
        return cursor.lastrowid

    def add_adjustment(self, batch_id, item, change, stock_before, stock_after):
        """One item changed. The item's name and the stock before and after are copied now."""
        self.execute(
            "INSERT INTO stock_adjustments (batch_id, item_id, item_name, change, stock_before, stock_after) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (batch_id, item["id"], item["name"], change, stock_before, stock_after),
        )

    def get_batch(self, batch_id):
        return self.one(
            f"SELECT {BATCH_COLUMNS} FROM stock_batches JOIN users ON users.id = stock_batches.user_id "
            "WHERE stock_batches.id = ?", (batch_id,))

    def batch_adjustments(self, batch_id):
        return self.all("SELECT * FROM stock_adjustments WHERE batch_id = ? ORDER BY id", (batch_id,))

    def find_batch_by_ref(self, user_id, client_ref):
        """The batch this person already saved with this reference, or None."""
        return self.one(
            f"SELECT {BATCH_COLUMNS} FROM stock_batches JOIN users ON users.id = stock_batches.user_id "
            "WHERE stock_batches.user_id = ? AND stock_batches.client_ref = ?", (user_id, client_ref))
