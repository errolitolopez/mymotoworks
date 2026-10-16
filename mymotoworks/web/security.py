"""Who is logged in, and decorators that let only the right people open a page or API."""

from functools import wraps

from flask import g, redirect, request, session, url_for

from mymotoworks.database import get_db
from mymotoworks.repositories import UserRepository


def current_user():
    """The logged-in user's row, or None. Deactivated users count as logged out."""
    if "user" not in g:
        g.user = None
        user_id = session.get("user_id")
        if user_id is not None:
            user = UserRepository(get_db()).get_active(user_id)
            if user is None:
                session.clear()
            g.user = user
    return g.user


def json_body():
    """The posted JSON object, or {} when there is none."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def login_required_page(view):
    """For HTML pages: send the user to the login page if not logged in."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("auth.login_page"))
        return view(*args, **kwargs)
    return wrapper
