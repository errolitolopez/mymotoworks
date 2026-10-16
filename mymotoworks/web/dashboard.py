"""The home page after login. Later tasks fill it (Sell for staff, Today for the admin)."""

from flask import Blueprint, render_template

from mymotoworks.web.security import current_user, login_required_page

bp = Blueprint("dashboard", __name__)


@bp.get("/dashboard")
@login_required_page
def page():
    return render_template("dashboard.html", user=current_user())
