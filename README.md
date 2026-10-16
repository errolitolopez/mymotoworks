# mymotoworks

Inventory, restock, sales and cash for Jaryl's Motoworks, a motor shop.

Built with Python (Flask), SQLite, vanilla JavaScript and Bootstrap 5.

## Getting started

Requires Python 3.10+.

    ./run.sh          # http://127.0.0.1:5000
    ./run.sh lan      # also reachable from other devices on the same Wi-Fi

## Tests

    .venv/bin/pytest

The plan and roadmap are in `docs/mymotoworks/plan.md` (in the ProjectWorkspace docs).

## Code structure

```
app.py                  entry point (flask --app app ...): app = create_app()
run.sh                  sets up the virtual environment and starts the app
mymotoworks/
  __init__.py           create_app(): config, database, error handlers, blueprints
  config.py             database path, secret key, cookie settings
  errors.py             ValidationError / NotFoundError / ... -> JSON {"error": ...}
  database.py           connection per request, init-db, default admin
  schema.sql            the tables
  repositories/         all SQL, one class per kind of data; they never commit
  web/                  Flask blueprints (pages + JSON API)
  templates/, static/   base.html, home.html, glass.css, theme.js
tests/                  pytest suite
```

Each layer only uses the ones below it: web → services → repositories / domain.
A route reads the request, calls a service, and returns JSON; a service raises
`ValidationError("...")` (or `NotFoundError`, ...) and the error becomes `{"error": "..."}`
with the right status, with nothing saved. (`services/` and `domain/` come with the first
features that need them.)

The default admin is `admin` / `admin`, created on the first start. Login and the forced
password change come in the next task.
