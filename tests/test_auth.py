"""Login and logout."""

from conftest import PASSWORD, db_execute, login


def post_login(client, username, password):
    return client.post("/api/login", json={"username": username, "password": password})


def test_login_works_and_opens_the_home_page(client):
    response = post_login(client, "staff1", PASSWORD)
    assert response.status_code == 200
    assert response.get_json()["must_change_password"] is False
    page = client.get("/dashboard")
    assert page.status_code == 200
    assert "Sample Staff" in page.get_data(as_text=True)


def test_default_admin_is_told_to_change_the_password(client):
    response = post_login(client, "admin", "admin")
    assert response.status_code == 200
    assert response.get_json()["must_change_password"] is True


def test_username_ignores_capitals_and_spaces(client):
    assert post_login(client, "  STAFF1 ", PASSWORD).status_code == 200


def test_wrong_password_and_unknown_user_give_the_same_message(client):
    wrong = post_login(client, "staff1", "nope")
    unknown = post_login(client, "nobody", "nope")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.get_json()["error"] == unknown.get_json()["error"] == "Wrong username or password."


def test_empty_fields_are_refused(client):
    response = post_login(client, "", "")
    assert response.status_code == 400
    assert response.get_json()["error"] == "Enter your username and password."


def test_non_text_values_and_no_body_do_not_crash(client):
    assert client.post("/api/login", json={"username": 123, "password": ["x"]}).status_code in (400, 401)
    assert client.post("/api/login").status_code == 400


def test_deactivated_account_cannot_log_in(client):
    db_execute("UPDATE users SET active = 0 WHERE username = 'staff1'")
    response = post_login(client, "staff1", PASSWORD)
    assert response.status_code == 403
    assert "deactivated" in response.get_json()["error"]


def test_deactivated_while_logged_in_is_logged_out():
    staff = login("staff1")
    assert staff.get("/dashboard").status_code == 200
    db_execute("UPDATE users SET active = 0 WHERE username = 'staff1'")
    response = staff.get("/dashboard")
    assert response.status_code == 302 and response.headers["Location"].endswith("/login")


def test_home_pages_send_a_visitor_to_login(client):
    for path in ("/", "/dashboard"):
        response = client.get(path)
        assert response.status_code == 302 and response.headers["Location"].endswith("/login")


def test_logged_in_user_skips_the_login_page():
    staff = login("staff1")
    assert staff.get("/login").headers["Location"].endswith("/dashboard")
    assert staff.get("/").headers["Location"].endswith("/dashboard")


def test_logout_ends_the_session():
    staff = login("staff1")
    assert staff.post("/api/logout").status_code == 200
    assert staff.get("/dashboard").status_code == 302


def test_login_page_has_the_theme_button(client):
    assert "data-theme-toggle" in client.get("/login").get_data(as_text=True)
