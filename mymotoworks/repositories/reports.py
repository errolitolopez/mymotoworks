"""SQL that adds things up for the reports. It only reads: it never changes data or commits."""

from mymotoworks.repositories.base import Repository

# A sale counts when it is approved and not voided: pending, rejected and voided sales are left out.
COUNTED_SALES = "sales.approved_at IS NOT NULL AND sales.voided_at IS NULL"
# The sums use the name, price and cost copied onto each sale line when it was sold.
LINE_SUMS = (
    "COUNT(DISTINCT sales.id) AS sales, SUM(sale_lines.qty) AS pieces, "
    "SUM(sale_lines.qty * sale_lines.benta) AS total, SUM(sale_lines.qty * sale_lines.puhunan) AS cost"
)


class ReportRepository(Repository):
    def sales_by_day(self, first, last):
        """One row per day with counted sales between two ISO dates (inclusive), oldest first."""
        return self.all(
            f"SELECT sales.sale_date AS day, {LINE_SUMS} FROM sales JOIN sale_lines ON sale_lines.sale_id = sales.id "
            f"WHERE sales.sale_date BETWEEN ? AND ? AND {COUNTED_SALES} GROUP BY sales.sale_date "
            "ORDER BY sales.sale_date", (first, last))

    def sales_by_month(self, first, last):
        """One row per month with counted sales between two ISO dates (inclusive), oldest first."""
        return self.all(
            f"SELECT substr(sales.sale_date, 1, 7) AS month, {LINE_SUMS} FROM sales "
            "JOIN sale_lines ON sale_lines.sale_id = sales.id "
            f"WHERE sales.sale_date BETWEEN ? AND ? AND {COUNTED_SALES} GROUP BY month ORDER BY month", (first, last))

    def restocked(self, first, last):
        """What the restocks of the period cost, in centavos. Voided restocks are left out."""
        return self.value(
            "SELECT COALESCE(SUM(total), 0) FROM restocks WHERE restock_date BETWEEN ? AND ? AND voided_at IS NULL",
            (first, last))

    def best_sellers(self, first, last, limit):
        """The items that sold the most pieces in the period, most first (ties by name)."""
        return self.all(
            "SELECT sale_lines.item_id AS item_id, sale_lines.item_name AS name, SUM(sale_lines.qty) AS pieces, "
            "SUM(sale_lines.qty * sale_lines.benta) AS total, "
            "SUM(sale_lines.qty * (sale_lines.benta - sale_lines.puhunan)) AS tubo "
            "FROM sales JOIN sale_lines ON sale_lines.sale_id = sales.id "
            f"WHERE sales.sale_date BETWEEN ? AND ? AND {COUNTED_SALES} "
            "GROUP BY sale_lines.item_id ORDER BY pieces DESC, name COLLATE NOCASE LIMIT ?", (first, last, limit))
