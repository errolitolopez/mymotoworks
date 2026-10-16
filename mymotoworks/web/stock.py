"""The stock pages and API. Admin only: only the owner corrects the stock."""

from flask import Blueprint, jsonify

from mymotoworks.database import get_db
from mymotoworks.services import StockService
from mymotoworks.web.security import current_user, json_body, role_required_api

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
