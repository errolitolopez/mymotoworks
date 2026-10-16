"""The production switch, the security headers, and the set-password command."""

from pathlib import Path

from mymotoworks import create_app

from conftest import PASSWORD, flask_app, login


def production_client(monkeypatch):
    """A client for an app started the way the host starts it (MYMOTOWORKS_PRODUCTION=1)."""
    monkeypatch.setenv("MYMOTOWORKS_PRODUCTION", "1")
    return create_app({"TESTING": True}).test_client()


def wrong_logins(client, headers, count=5):
    for _ in range(count):
        client.post("/api/login", json={"username": "staff1", "password": "nope"}, headers=headers)


def test_behind_the_proxy_the_lockout_counts_the_real_visitor(monkeypatch):
    client = production_client(monkeypatch)
    wrong_logins(client, {"X-Forwarded-For": "1.1.1.1"})
    locked = client.post("/api/login", json={"username": "staff1", "password": PASSWORD},
                         headers={"X-Forwarded-For": "1.1.1.1"})
    other = client.post("/api/login", json={"username": "staff1", "password": PASSWORD},
                        headers={"X-Forwarded-For": "2.2.2.2"})
    assert locked.status_code == 429 and other.status_code == 200


def test_without_the_switch_a_forged_forwarding_header_is_ignored(client):
    wrong_logins(client, {"X-Forwarded-For": "1.1.1.1"})
    for forged in ("2.2.2.2", "3.3.3.3"):
        response = client.post("/api/login", json={"username": "staff1", "password": PASSWORD},
                               headers={"X-Forwarded-For": forged})
        assert response.status_code == 429  # still the same visitor: the header changed nothing


def cookie_headers(response):
    return response.headers.getlist("Set-Cookie")


def test_the_cookie_is_secure_in_production_and_not_here(monkeypatch, client):
    here = client.post("/api/login", json={"username": "staff1", "password": PASSWORD})
    assert cookie_headers(here) and not any("Secure" in header for header in cookie_headers(here))
    there = production_client(monkeypatch).post("/api/login", json={"username": "staff1", "password": PASSWORD})
    assert cookie_headers(there) and all("Secure" in header and "HttpOnly" in header for header in cookie_headers(there))


def test_every_answer_has_the_safety_headers(client):
    response = client.get("/login")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "same-origin"


def test_the_api_and_the_downloads_are_not_cached(admin):
    for path in ("/api/items", "/api/reports/sales", "/reports/stock.xlsx"):
        assert admin.get(path).headers["Cache-Control"] == "no-store", path
    assert "no-store" not in admin.get("/login").headers.get("Cache-Control", "")


def run_set_password(args, answers):
    return flask_app.test_cli_runner().invoke(args=["set-password", *args], input=answers)


def test_set_password_sets_a_password_and_ends_the_forced_change():
    result = run_set_password(["admin"], "goodpass1\ngoodpass1\n")
    assert result.exit_code == 0 and "Password set for admin." in result.output
    assert "goodpass1" not in result.output
    client = login("admin", "goodpass1")
    assert client.get("/dashboard").status_code == 200  # no forced change page in between


def test_set_password_refuses_a_weak_password_and_changes_nothing():
    result = run_set_password(["admin"], "abc\nabc\n")
    assert result.exit_code != 0 and "at least 6 characters" in result.output
    assert flask_app.test_client().post("/api/login", json={"username": "admin", "password": "admin"}).status_code == 200


def test_set_password_refuses_the_username_as_the_password():
    result = run_set_password(["staff1"], "staff1\nstaff1\n")
    assert result.exit_code != 0 and "can't be your username" in result.output


def test_a_mismatch_changes_nothing():
    result = run_set_password(["admin"], "goodpass1\nother-pass\n")
    assert result.exit_code != 0
    assert flask_app.test_client().post("/api/login", json={"username": "admin", "password": "admin"}).status_code == 200


def test_set_password_for_an_unknown_user():
    result = run_set_password(["nobody"], "goodpass1\ngoodpass1\n")
    assert result.exit_code != 0 and "no user" in result.output.lower()


def test_the_gitignore_keeps_data_and_secrets_out_of_git():
    lines = (Path(__file__).resolve().parent.parent / ".gitignore").read_text().splitlines()
    for pattern in ("instance/", "*.db", "*.xlsx", "backups/", ".venv/"):
        assert pattern in lines, pattern
