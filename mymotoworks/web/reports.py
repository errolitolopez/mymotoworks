"""The Reports page, its API and the Excel downloads. Admin only."""

from flask import Blueprint, jsonify, render_template, request

from mymotoworks.database import get_db
from mymotoworks.services import ReportService
from mymotoworks.web.security import current_user, role_required_api, role_required_page

bp = Blueprint("reports", __name__)


def service():
    return ReportService(get_db(), current_user())


@bp.get("/reports")
@role_required_page("admin")
def page():
    return render_template("reports.html", user=current_user())


def _single(name):
    """The one value of a query parameter. Sending it twice is a bad request, not a guess."""
    values = request.args.getlist(name)
    return values[0] if len(values) == 1 else (None if not values else object())


@bp.get("/api/reports/sales")
@role_required_api("admin")
def api_sales():
    """?month=2026-10 (this month when missing or empty)."""
    return jsonify(service().sales(_single("month")))


@bp.get("/api/reports/months")
@role_required_api("admin")
def api_months():
    """?year=2026 (this year when missing or empty)."""
    return jsonify(service().months(_single("year")))


@bp.get("/api/reports/stock")
@role_required_api("admin")
def api_stock():
    """The value of the stock, the low and below-zero items, and where the most money sits."""
    return jsonify(service().stock())
