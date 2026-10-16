"""Report use cases: shape the sums into the answers the Reports page and the downloads use."""

from mymotoworks import config
from mymotoworks.domain.reports import month_range, parse_month, parse_year
from mymotoworks.repositories import ReportRepository
from mymotoworks.services.base import Service

BEST_SELLER_LIMIT = 10


def _money(row):
    """A row of sums as the answer: cost and tubo next to the total (tubo = total - cost)."""
    return {"sales": row["sales"], "pieces": row["pieces"], "total": row["total"], "cost": row["cost"],
            "tubo": row["total"] - row["cost"]}


class ReportService(Service):
    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.reports = ReportRepository(db)

    def sales(self, month_text=None):
        """The sales of one month: a line per day with sales, the month's totals, what the restocks
        cost, and the best sellers. Only approved sales that are not voided count."""
        today = config.shop_today()
        year, month = parse_month(month_text, (today.year, today.month))
        first, last = month_range(year, month)
        days = [{"date": row["day"], **_money(row)} for row in self.reports.sales_by_day(first, last)]
        totals = {key: sum(day[key] for day in days) for key in ("sales", "pieces", "total", "cost", "tubo")}
        return {
            "month": f"{year:04d}-{month:02d}",
            "days": days,
            "totals": totals,
            "restocked": self.reports.restocked(first, last),
            "best_sellers": [
                {"item_id": row["item_id"], "name": row["name"], "pieces": row["pieces"], "total": row["total"],
                 "tubo": row["tubo"]}
                for row in self.reports.best_sellers(first, last, BEST_SELLER_LIMIT)
            ],
        }

    def months(self, year_text=None):
        """The months of one year that had sales, with each month's totals."""
        year = parse_year(year_text, config.shop_today().year)
        rows = self.reports.sales_by_month(f"{year:04d}-01-01", f"{year:04d}-12-31")
        return {"year": year, "months": [{"month": row["month"], **_money(row)} for row in rows]}

    STOCK_LIST_LIMIT = 200
    TOP_CAPITAL_LIMIT = 10
    EXPORT_LIMIT = 5000

    @staticmethod
    def _stock_item(row):
        return {"id": row["id"], "name": row["name"], "model": row["model"], "part_no": row["part_no"],
                "stock": row["stock"], "reorder_level": row["reorder_level"], "puhunan": row["puhunan"],
                "benta": row["benta"], "capital": row["capital"]}

    def stock(self):
        """The value of the stock on the shelves, the items that are low or below zero, and where the
        most money sits. Only active items that count stock; a stock below 0 counts as 0 in the values."""
        totals = self.reports.stock_totals()
        low = self.reports.stock_items("stock <= reorder_level", "stock, name COLLATE NOCASE", self.STOCK_LIST_LIMIT)
        below_zero = self.reports.stock_items("stock < 0", "stock, name COLLATE NOCASE", self.STOCK_LIST_LIMIT)
        top = self.reports.stock_items("stock > 0", "capital DESC, name COLLATE NOCASE", self.TOP_CAPITAL_LIMIT)
        return {
            "totals": {
                "items": totals["items"], "pieces": totals["pieces"], "capital": totals["capital"],
                "revenue": totals["revenue"], "tubo": totals["revenue"] - totals["capital"],
                "out_of_stock": totals["out_of_stock"], "low_stock": totals["low"], "below_zero": totals["below_zero"],
            },
            "low_stock": [self._stock_item(row) for row in low],
            "below_zero": [self._stock_item(row) for row in below_zero],
            "top_capital": [self._stock_item(row) for row in top],
        }

    def stock_items(self):
        """Every active item that counts stock, by name, for the Excel file."""
        rows = self.reports.stock_items("1 = 1", "name COLLATE NOCASE, model COLLATE NOCASE", self.EXPORT_LIMIT)
        return [self._stock_item(row) for row in rows]
