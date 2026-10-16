"""SQL for the sales and sale_lines tables. It never commits: the service does."""

from mymotoworks.repositories.base import Repository


class SaleRepository(Repository):
    def create(self, sale_date, user_id, total, client_ref):
        cursor = self.execute(
            "INSERT INTO sales (sale_date, user_id, total, client_ref) VALUES (?, ?, ?, ?)",
            (sale_date, user_id, total, client_ref),
        )
        return cursor.lastrowid

    def add_line(self, sale_id, item, qty, benta):
        """One line. The item's name, puhunan and whether its stock is counted are copied now."""
        self.execute(
            "INSERT INTO sale_lines (sale_id, item_id, item_name, qty, puhunan, benta, tracked) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sale_id, item["id"], item["name"], qty, item["puhunan"], benta, item["track_stock"]),
        )

    def get(self, sale_id):
        return self.one(
            "SELECT sales.*, users.name AS user_name FROM sales JOIN users ON users.id = sales.user_id "
            "WHERE sales.id = ?", (sale_id,))

    def lines(self, sale_id):
        return self.all("SELECT * FROM sale_lines WHERE sale_id = ? ORDER BY id", (sale_id,))

    def find_by_ref(self, user_id, client_ref):
        """The sale this person already saved with this reference, or None."""
        return self.one(
            "SELECT sales.*, users.name AS user_name FROM sales JOIN users ON users.id = sales.user_id "
            "WHERE sales.user_id = ? AND sales.client_ref = ?", (user_id, client_ref))
