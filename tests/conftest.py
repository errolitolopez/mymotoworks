"""Shared test setup: the app and a test client.

Run with: .venv/bin/pytest
"""

import os
import sqlite3
import tempfile

import pytest
from werkzeug.security import generate_password_hash

# The app reads its database path from MYMOTOWORKS_DATABASE when it is imported.
_DB_DIR = tempfile.mkdtemp(prefix="mymotoworks-tests-")
os.environ["MYMOTOWORKS_DATABASE"] = os.path.join(_DB_DIR, "test.db")

from app import app as flask_app  # noqa: E402  (must come after setting the database path)


from mymotoworks.database import get_db  # noqa: E402
from mymotoworks.repositories import UserRepository  # noqa: E402

PASSWORD = "1234"  # the sample staff account
ADMIN_PASSWORD = "adminpass1"  # the admin after the forced password change


def seed_staff():
    """A sample staff account: staff1 / 1234, no password change needed."""
    with flask_app.app_context():
        db = get_db()
        UserRepository(db).create("Sample Staff", "staff1", generate_password_hash(PASSWORD), "staff", 0)
        db.commit()


def db_execute(sql, params=()):
    """Change the test database directly (for setting up a situation the API cannot make)."""
    with flask_app.app_context():
        db = get_db()
        db.execute(sql, params)
        db.commit()


def login(username, password=PASSWORD):
    """A test client logged in as this user."""
    client = flask_app.test_client()
    response = client.post("/api/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.get_json()
    return client


def reset_database():
    """Empty every table, then create the default admin again."""
    connection = sqlite3.connect(os.environ["MYMOTOWORKS_DATABASE"])
    tables = [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
    connection.execute("PRAGMA foreign_keys = OFF")
    for table in tables:
        connection.execute(f"DELETE FROM {table}")
    if connection.execute("SELECT 1 FROM sqlite_master WHERE name = 'sqlite_sequence'").fetchone():
        connection.execute("DELETE FROM sqlite_sequence")
    connection.commit()
    connection.close()
    assert flask_app.test_cli_runner().invoke(args=["init-db"]).exit_code == 0
    seed_staff()


@pytest.fixture(autouse=True)
def fresh_login_throttle():
    """Forget wrong-password counts from earlier tests."""
    flask_app.extensions["login_throttle"].reset()
    yield


@pytest.fixture(autouse=True)
def fresh_database():
    reset_database()
    yield


@pytest.fixture
def app():
    return flask_app


@pytest.fixture
def client():
    return flask_app.test_client()


@pytest.fixture
def admin():
    """The default admin, logged in, after the forced password change."""
    client = login("admin", "admin")
    response = client.post("/api/change-password",
                           json={"current_password": "admin", "new_password": ADMIN_PASSWORD})
    assert response.status_code == 200, response.get_json()
    return client
