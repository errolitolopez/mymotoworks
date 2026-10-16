"""The home page. Task 2 replaces it with the login redirect and the real pages."""

from flask import Blueprint, render_template

bp = Blueprint("pages", __name__)


@bp.get("/")
def home():
    return render_template("home.html")
