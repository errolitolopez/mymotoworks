"""App settings that aren't business rules: where things are stored and cookie settings."""

import os
import secrets
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Shop days are calendar days in the shop's time zone, wherever the server runs.
SHOP_TIMEZONE = ZoneInfo("Asia/Manila")


def shop_today():
    """Today's date at the shop."""
    return datetime.now(SHOP_TIMEZONE).date()


def is_production():
    """True when the host asked for production behavior (MYMOTOWORKS_PRODUCTION=1 in its WSGI file). It is
    never set on a developer's computer: its secure cookie would not work over plain http."""
    return os.environ.get("MYMOTOWORKS_PRODUCTION") == "1"


def configure(app, test_config=None):
    """Set the database path, secret key and cookie settings on the Flask app."""
    # The instance/ folder holds private files (database, secret key). It is not committed to git.
    os.makedirs(app.instance_path, exist_ok=True)
    app.config["DATABASE"] = os.environ.get(
        "MYMOTOWORKS_DATABASE", os.path.join(app.instance_path, "mymotoworks.db"))
    # No "remember me": the login ends when the browser is closed, since shop phones are shared.
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if is_production():
        # The site is served over https, so the login cookie may never travel over plain http.
        app.config["SESSION_COOKIE_SECURE"] = True
        app.config["PREFERRED_URL_SCHEME"] = "https"
    app.secret_key = load_secret_key(app.instance_path)
    if test_config:
        app.config.update(test_config)


def load_secret_key(instance_path):
    """The secret key signs the login cookie. Create one the first time and reuse it after."""
    path = os.path.join(instance_path, "secret_key")
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
    with open(path) as f:
        return f.read().strip()


def shop_time_text(utc_text):
    """"2026-10-16 02:30:00" (the database's UTC time) -> "10:30" at the shop."""
    moment = datetime.strptime(utc_text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return moment.astimezone(SHOP_TIMEZONE).strftime("%H:%M")
