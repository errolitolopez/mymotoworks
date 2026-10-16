"""The stock pages and API. Admin only: only the owner corrects the stock."""

from flask import Blueprint, jsonify, render_template, request

from mymotoworks.database import get_db
from mymotoworks.services import StockService
from mymotoworks.web.security import current_user, json_body, role_required_api, role_required_page

bp = Blueprint("stock", __name__)


def service():
    return StockService(get_db(), current_user())


@bp.post("/api/stock-adjustments")
@role_required_api("admin")
def api_adjust():
    """Body: {reason, note?, client_ref?, lines: [{item_id, change}]}. A change is negative to take out.
    201 for a new save, 200 when it was already saved."""
    result = service().adjust(json_body())
    return jsonify(result), 200 if result["duplicate"] else 201


@bp.get("/stock-history")
@role_required_page("admin")
def history_page():
    return render_template("stock_history.html", user=current_user())


@bp.get("/api/stock-adjustments")
@role_required_api("admin")
def api_list():
    """?item= (an item id; a bad value means all items), ?page= and ?per_page= (20 by default, at most 50)."""
    args = request.args
    return jsonify(service().list(
        item_id=args.get("item", type=int),
        page=args.get("page", 1, type=int),
        per_page=args.get("per_page", StockService.DEFAULT_PER_PAGE, type=int),
    ))


@bp.get("/stock-count")
@role_required_page("admin")
def count_page():
    return render_template("stock_count.html", user=current_user())


@bp.post("/api/stock-counts")
@role_required_api("admin")
def api_count():
    """Body: {note?, client_ref?, lines: [{item_id, counted}]}. Sets each counted item's stock to the
    counted number. 201 when something changed, 200 when nothing changed or it was already saved."""
    result = service().count(json_body())
    return jsonify(result), 201 if result["changed"] and not result["duplicate"] else 200
