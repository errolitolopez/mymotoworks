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
    """?inactive=1 also lists deactivated items (admin only)."""
    return jsonify(service().list(inactive=request.args.get("inactive") == "1"))


@bp.post("/api/items")
@role_required_api("admin")
def api_create():
    return jsonify(item=service().create(json_body())), 201
