"""Shared test setup: the app and a test client.

Run with: .venv/bin/pytest
"""

import os
import sqlite3
import tempfile

import pytest

# The app reads its database path from MYMOTOWORKS_DATABASE when it is imported.
_DB_DIR = tempfile.mkdtemp(prefix="mymotoworks-tests-")
os.environ["MYMOTOWORKS_DATABASE"] = os.path.join(_DB_DIR, "test.db")

from app import app as flask_app  # noqa: E402  (must come after setting the database path)


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
