"""The home page after login. Later tasks fill it (Sell for staff, Today for the admin)."""

from flask import Blueprint, render_template

from mymotoworks.database import get_db
from mymotoworks.services import BackupService, SaleService
from mymotoworks.web.security import current_user, login_required_page

bp = Blueprint("dashboard", __name__)


@bp.get("/dashboard")
@login_required_page
def page():
    user = current_user()
    # The admin is told about staff sales that wait for approval, so none is forgotten.
    pending = SaleService(get_db(), user).pending_overview() if user["role"] == "admin" else None
    backup = BackupService(get_db(), user).status() if user["role"] == "admin" else None
    return render_template("dashboard.html", user=user, pending=pending, backup=backup)
