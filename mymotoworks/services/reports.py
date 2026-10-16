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
