"""The Items page and its API. Everyone logged in can look; only the admin changes items."""

from flask import Blueprint, jsonify, render_template, request

from mymotoworks.database import get_db
from mymotoworks.services import ItemService
from mymotoworks.web.security import (
    current_user, json_body, login_required_api, login_required_page, role_required_api,
)

bp = Blueprint("items", __name__)


def service():
    return ItemService(get_db(), current_user())


@bp.get("/items")
@login_required_page
def page():
    return render_template("items.html", user=current_user())


@bp.get("/api/items")
@login_required_api
def api_list():
    """?q= words to find, ?low=1 low stock only, ?inactive=1 also deactivated (admin only),
    ?page= and ?per_page= (50 by default, at most 100). A bad number means the default."""
    args = request.args
    return jsonify(service().list(
        query=args.get("q", ""),
        low=args.get("low") == "1",
        inactive=args.get("inactive") == "1",
        page=args.get("page", 1, type=int),
        per_page=args.get("per_page", ItemService.DEFAULT_PER_PAGE, type=int),
    ))


@bp.post("/api/items")
@role_required_api("admin")
def api_create():
    return jsonify(item=service().create(json_body())), 201
