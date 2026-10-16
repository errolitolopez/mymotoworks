"""The Users page and API (admin only)."""

from conftest import PASSWORD, login


def create(admin, **fields):
    data = {"name": "New Person", "username": "newperson", "role": "staff", **fields}
    return admin.post("/api/users", json=data)


def usernames(response):
    return [user["username"] for user in response.get_json()["users"]]


def user_id(admin, username):
    return next(u["id"] for u in admin.get("/api/users").get_json()["users"] if u["username"] == username)


def test_admin_lists_accounts_without_password_hashes(admin):
    response = admin.get("/api/users")
    assert response.status_code == 200
    assert set(usernames(response)) == {"admin", "staff1"}
    assert "password_hash" not in response.get_data(as_text=True)


def test_staff_cannot_use_the_users_api_or_page():
    staff = login("staff1")
    assert staff.get("/api/users").status_code == 403
    assert staff.post("/api/users", json={}).status_code == 403
    assert staff.put("/api/users/1", json={"active": False}).status_code == 403
    page = staff.get("/users")
    assert page.status_code == 302 and page.headers["Location"].endswith("/dashboard")


def test_logged_out_visitor_gets_401_and_login_redirect(client):
    assert client.get("/api/users").status_code == 401
    assert client.get("/users").status_code == 302


def test_temporary_password_user_cannot_use_the_api_yet():
    admin = login("admin", "admin")
    response = admin.get("/api/users")
    assert response.status_code == 403 and response.get_json()["must_change_password"] is True


def test_create_staff_gives_a_temporary_password_shown_once(admin):
    response = create(admin)
    assert response.status_code == 201
    data = response.get_json()
    temp = data["temp_password"]
    assert len(temp) == 10
    assert data["user"]["role"] == "staff" and data["user"]["must_change_password"] is True
    assert "temp_password" not in admin.get("/api/users").get_data(as_text=True)
    # The new person logs in with it and must change it.
    new = login("newperson", temp)
    assert new.get("/dashboard").status_code == 302


def test_create_an_admin_account(admin):
    assert create(admin, username="admin2", role="admin").get_json()["user"]["role"] == "admin"


def test_create_rules(admin):
    username_message = "Username must be 3 to 30 letters, numbers, dots, dashes or underscores."
    cases = [
        ({"name": ""}, "Name is required."),
        ({"name": "x" * 101}, "Name can be at most 100 characters."),
        ({"username": "ab"}, username_message),
        ({"username": "has space"}, username_message),
        ({"role": "teacher"}, "Choose a role: admin or staff."),
        ({"role": None}, "Choose a role: admin or staff."),
    ]
    for fields, message in cases:
        response = create(admin, **fields)
        assert response.status_code == 400 and response.get_json()["error"] == message, fields


def test_username_is_trimmed_lowercased_and_unique(admin):
    first = create(admin, username="  Staff2 ")
    assert first.status_code == 201 and first.get_json()["user"]["username"] == "staff2"
    for username in ("staff2", "STAFF2", "Staff1", "ADMIN"):
        response = create(admin, username=username)
        assert response.status_code == 400
        assert response.get_json()["error"] == "That username is taken."


def test_rename(admin):
    staff_id = user_id(admin, "staff1")
    response = admin.put(f"/api/users/{staff_id}", json={"name": "  Maria   Santos "})
    assert response.status_code == 200 and response.get_json()["user"]["name"] == "Maria Santos"
    assert admin.put(f"/api/users/{staff_id}", json={"name": " "}).status_code == 400


def test_reset_password_makes_a_new_temporary_one(admin, client):
    staff_id = user_id(admin, "staff1")
    response = admin.put(f"/api/users/{staff_id}", json={"reset_password": True})
    temp = response.get_json()["temp_password"]
    assert response.get_json()["user"]["must_change_password"] is True
    assert client.post("/api/login", json={"username": "staff1", "password": PASSWORD}).status_code == 401
    assert login("staff1", temp).get("/dashboard").status_code == 302


def test_deactivate_and_activate(admin, client):
    staff_id = user_id(admin, "staff1")
    staff = login("staff1")
    off = admin.put(f"/api/users/{staff_id}", json={"active": False})
    assert off.get_json()["user"]["active"] is False
    assert staff.get("/dashboard").status_code == 302  # the open session ends
    assert client.post("/api/login", json={"username": "staff1", "password": PASSWORD}).status_code == 403
    on = admin.put(f"/api/users/{staff_id}", json={"active": True})
    assert on.get_json()["user"]["active"] is True
    assert login("staff1").get("/dashboard").status_code == 200


def test_admin_cannot_deactivate_their_own_account(admin):
    response = admin.put(f"/api/users/{user_id(admin, 'admin')}", json={"active": False})
    assert response.status_code == 400
    assert response.get_json()["error"] == "You can't deactivate your own account."
    assert admin.get("/api/users").status_code == 200


def test_unknown_account_is_not_found(admin):
    assert admin.put("/api/users/9999", json={"name": "x"}).status_code == 404


def test_search_by_name_or_username(admin):
    create(admin, name="Maria Santos", username="msantos")
    assert usernames(admin.get("/api/users?q=maria")) == ["msantos"]
    assert usernames(admin.get("/api/users?q=SANTOS")) == ["msantos"]
    assert usernames(admin.get("/api/users?q=staff1")) == ["staff1"]


def test_search_treats_percent_and_underscore_as_plain_text(admin):
    assert usernames(admin.get("/api/users?q=%25")) == []
    assert usernames(admin.get("/api/users?q=_")) == []


def test_users_page_opens_for_admin(admin):
    page = admin.get("/users")
    assert page.status_code == 200 and "Users" in page.get_data(as_text=True)
