"""Shared test setup: the app and a test client.

Run with: .venv/bin/pytest
"""

import os
import tempfile

import pytest

# The app reads its database path from MYMOTOWORKS_DATABASE when it is imported. The database
# itself comes in Feature B, which adds a reset before each test.
_DB_DIR = tempfile.mkdtemp(prefix="mymotoworks-tests-")
os.environ["MYMOTOWORKS_DATABASE"] = os.path.join(_DB_DIR, "test.db")

from app import app as flask_app  # noqa: E402  (must come after setting the database path)


@pytest.fixture
def app():
    return flask_app


@pytest.fixture
def client():
    return flask_app.test_client()
