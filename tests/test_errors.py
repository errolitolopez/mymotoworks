"""A failed request answers {"error": "..."} with the right status, and nothing is saved."""

import pytest

from mymotoworks import create_app
from mymotoworks.database import get_db
from mymotoworks.errors import (
    ForbiddenError, NotFoundError, TooManyRequestsError, UnauthorizedError, ValidationError,
)

CASES = [
    (ValidationError, 400),
    (NotFoundError, 404),
    (ForbiddenError, 403),
    (UnauthorizedError, 401),
    (TooManyRequestsError, 429),
]


@pytest.fixture
def error_client():
    """A separate app (the shared one has already served requests) with a route that fails."""
    app = create_app({"TESTING": True})

    @app.get("/boom/<name>")
    def boom(name):
        errors = {cls.__name__: cls for cls, _ in CASES}
        raise errors[name]("It failed.", must_change_password=True)

    @app.get("/boom-after-write")
    def boom_after_write():
        db = get_db()
        db.execute("INSERT INTO settings (key, value) VALUES ('leftover', '1')")
        raise ValidationError("Stop.")  # no commit: the write must be thrown away

    return app.test_client(), app


@pytest.mark.parametrize("error_class, status", CASES)
def test_each_error_uses_its_own_status(error_client, error_class, status):
    client, _ = error_client
    response = client.get(f"/boom/{error_class.__name__}")
    assert response.status_code == status
    assert response.get_json()["error"] == "It failed."


def test_extra_fields_are_in_the_json(error_client):
    client, _ = error_client
    assert client.get("/boom/ValidationError").get_json()["must_change_password"] is True


def test_a_failed_request_saves_nothing(error_client):
    client, app = error_client
    assert client.get("/boom-after-write").status_code == 400
    with app.app_context():
        assert get_db().execute("SELECT 1 FROM settings WHERE key = 'leftover'").fetchone() is None
