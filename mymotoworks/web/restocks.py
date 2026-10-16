"""The Restock pages and API. Admin only: only the owner records what arrived."""

from flask import Blueprint, jsonify, render_template

from mymotoworks import config
from mymotoworks.database import get_db
from mymotoworks.services import RestockService
from mymotoworks.web.security import current_user, json_body, role_required_api, role_required_page

bp = Blueprint("restocks", __name__)


def service():
    return RestockService(get_db(), current_user())


@bp.get("/restock")
@role_required_page("admin")
def new_page():
    return render_template("restock.html", user=current_user(), today=config.shop_today().isoformat())


@bp.get("/restocks")
@role_required_page("admin")
def history_page():
    # The history page itself comes in feature B; until then the link goes to the new-restock page.
    return render_template("restock.html", user=current_user(), today=config.shop_today().isoformat())


@bp.post("/api/restocks")
@role_required_api("admin")
def api_create():
    """Body: {lines: [{item_id, qty, puhunan?}], restock_date?, note?, client_ref?}. 201 for a new
    restock, 200 when it was already saved."""
    result = service().create(json_body())
    return jsonify(result), 200 if result["duplicate"] else 201
