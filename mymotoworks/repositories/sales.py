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

    def list_for_day(self, sale_date):
        """Every sale of the day, newest first, voided ones too."""
        return self.all(
            "SELECT sales.*, users.name AS user_name FROM sales JOIN users ON users.id = sales.user_id "
            "WHERE sales.sale_date = ? ORDER BY sales.id DESC", (sale_date,))

    def day_totals(self, sale_date):
        """{"count", "total", "tubo"} of the valid (not voided) sales of the day."""
        row = self.one(
            "SELECT COUNT(*) AS count, COALESCE(SUM(total), 0) AS total FROM sales "
            "WHERE sale_date = ? AND voided_at IS NULL", (sale_date,))
        tubo = self.value(
            "SELECT COALESCE(SUM((sale_lines.benta - sale_lines.puhunan) * sale_lines.qty), 0) "
            "FROM sale_lines JOIN sales ON sales.id = sale_lines.sale_id "
            "WHERE sales.sale_date = ? AND sales.voided_at IS NULL", (sale_date,))
        return {"count": row["count"], "total": row["total"], "tubo": tubo}

    def mark_voided(self, sale_id, user_id, reason):
        self.execute(
            "UPDATE sales SET voided_at = CURRENT_TIMESTAMP, voided_by = ?, void_reason = ? WHERE id = ?",
            (user_id, reason, sale_id))
