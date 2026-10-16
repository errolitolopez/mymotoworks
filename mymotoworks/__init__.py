"""mymotoworks: inventory, restock, sales and cash for Jaryl's Motoworks.

Layers (each only uses the ones below it):
  web/           Flask blueprints: pages and JSON API, login/role checks
  services/      use cases (one class per area), commit when the work is done
  repositories/  all SQL, one class per kind of data
  domain/        rules with no Flask or SQL: money, cash on hand, stock rules
"""

from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix

from mymotoworks import commands, config, database, imports, seed
from mymotoworks.errors import register_error_handlers
from mymotoworks.services import LoginThrottle
from mymotoworks.web import BLUEPRINTS


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    config.configure(app, test_config)
    if config.is_production():
        # Behind the host's proxy every request seems to come from the proxy. Trust exactly one proxy, so
        # the login lockout counts the real visitor. Never done on a developer's computer, where anybody
        # could send a forged X-Forwarded-For header.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    database.init_app(app)
    app.cli.add_command(seed.seed_command)
    app.cli.add_command(imports.import_items_command)
    app.cli.add_command(commands.set_password_command)
    app.cli.add_command(commands.backup_command)
    register_error_handlers(app)
    app.extensions["login_throttle"] = LoginThrottle()
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)

    @app.after_request
    def add_safety_headers(response):
        """Small protections on every answer, and no caching of shop data."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.path.startswith("/api/") or request.path.endswith(".xlsx"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return app
