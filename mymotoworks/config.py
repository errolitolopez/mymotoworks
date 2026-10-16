"""App settings that aren't business rules: where things are stored and cookie settings."""

import os
import secrets


def configure(app, test_config=None):
    """Set the database path, secret key and cookie settings on the Flask app."""
    # The instance/ folder holds private files (database, secret key). It is not committed to git.
    os.makedirs(app.instance_path, exist_ok=True)
    app.config["DATABASE"] = os.environ.get(
        "MYMOTOWORKS_DATABASE", os.path.join(app.instance_path, "mymotoworks.db"))
    # No "remember me": the login ends when the browser is closed, since shop phones are shared.
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
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
