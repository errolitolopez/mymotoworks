"""The Sell page and the sales API."""

from flask import Blueprint, jsonify, render_template, request

from mymotoworks import config
from mymotoworks.database import get_db
from mymotoworks.services import SaleService
from mymotoworks.web.security import current_user, json_body, login_required_api, login_required_page

bp = Blueprint("sales", __name__)


def service():
    return SaleService(get_db(), current_user())


@bp.get("/sell")
@login_required_page
def sell_page():
    return render_template("sell.html", user=current_user(), today=config.shop_today().isoformat())


@bp.post("/api/sales")
@login_required_api
def api_create():
    """Body: {lines: [{item_id, qty, benta?}], sale_date?, client_ref?}. 201 for a new sale,
    200 when this cart was already saved."""
    result = service().create(json_body())
    return jsonify(result), 200 if result["duplicate"] else 201


@bp.get("/sales")
@login_required_page
def history_page():
    return render_template("sales.html", user=current_user(), today=config.shop_today().isoformat())


@bp.get("/api/sales")
@login_required_api
def api_list():
    """?date=YYYY-MM-DD (today when missing). Staff may only ask for today."""
    return jsonify(service().list_day(request.args.get("date")))
