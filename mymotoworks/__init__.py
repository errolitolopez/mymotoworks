"""mymotoworks: inventory, restock, sales and cash for Jaryl's Motoworks.

Layers (each only uses the ones below it):
  web/           Flask blueprints: pages and JSON API, login/role checks
  services/      use cases (one class per area), commit when the work is done
  repositories/  all SQL, one class per kind of data
  domain/        rules with no Flask or SQL: money, cash on hand, stock rules
"""

from flask import Flask

from mymotoworks import config, database, seed
from mymotoworks.errors import register_error_handlers
from mymotoworks.services import LoginThrottle
from mymotoworks.web import BLUEPRINTS


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    config.configure(app, test_config)

    database.init_app(app)
    app.cli.add_command(seed.seed_command)
    register_error_handlers(app)
    app.extensions["login_throttle"] = LoginThrottle()
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)

    return app
