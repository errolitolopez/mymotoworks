"""Items: add, list, search, edit and deactivate."""

from conftest import add_items, db_execute, login, make_item


def items(response):
    return response.get_json()["items"]


def test_admin_adds_an_item_and_sees_it_in_the_list(admin):
    item = make_item(admin)
    assert item["name"] == "AIR FILTER SUNTAL"
    assert item["puhunan"] == 10350 and item["benta"] == 15000
    assert item["tubo"] == 4650
    assert item["stock"] == 3 and item["active"] is True
    assert [row["id"] for row in items(admin.get("/api/items"))] == [item["id"]]


def test_staff_see_items_without_any_cost_field(admin):
    make_item(admin)
    staff = login("staff1")
    response = staff.get("/api/items")
    assert response.status_code == 200
    assert items(response)[0]["benta"] == 15000
    text = response.get_data(as_text=True)
    assert "puhunan" not in text and "tubo" not in text


def test_staff_cannot_add_and_visitors_are_refused(admin, client):
    staff = login("staff1")
    assert staff.post("/api/items", json={"name": "X", "benta": 100}).status_code == 403
    assert client.get("/api/items").status_code == 401
    assert client.post("/api/items", json={}).status_code == 401


def test_error_answers_for_staff_leak_no_cost_field(admin):
    make_item(admin)
    staff = login("staff1")
    text = staff.post("/api/items", json={"name": "X", "puhunan": 5, "benta": 100}).get_data(as_text=True)
    assert "puhunan" not in text


def test_model_and_part_no_are_optional_and_trimmed(admin):
    item = make_item(admin, name="  ARMAK TAPE 5 YARDS ", model=None, part_no="  ")
    assert item["name"] == "ARMAK TAPE 5 YARDS"
    assert item["model"] == "" and item["part_no"] == ""


def test_missing_puhunan_counts_as_zero(admin):
    response = admin.post("/api/items", json={"name": "LINIS", "benta": 5000, "track_stock": False})
    assert response.status_code == 201
    assert response.get_json()["item"]["puhunan"] == 0
    assert response.get_json()["item"]["tubo"] == 5000


def test_same_name_for_different_models_is_allowed(admin):
    make_item(admin, model="NMAX V1", part_no="YA040D")
    make_item(admin, model="MIO SOUL", part_no="YA040")
    assert len(items(admin.get("/api/items"))) == 2


def test_untracked_item_gets_stock_zero_and_is_never_low(admin):
    item = make_item(admin, name="LINIS", track_stock=False, stock=9, reorder_level=4)
    assert item["stock"] == 0 and item["reorder_level"] == 0
    assert item["track_stock"] is False and item["low_stock"] is False


def test_low_stock_flag(admin):
    assert make_item(admin, stock=2, reorder_level=2)["low_stock"] is True
    assert make_item(admin, stock=3, reorder_level=2)["low_stock"] is False


def test_item_rules(admin):
    money = "{} must be an amount from 0 to 1,000,000 pesos."
    count = "{} must be a whole number from 0 to 1000000."
    cases = [
        ({"name": ""}, "Item name is required."),
        ({"name": "x" * 121}, "Item name can be at most 120 characters."),
        ({"model": "x" * 61}, "Model can be at most 60 characters."),
        ({"part_no": "x" * 61}, "Part no. can be at most 60 characters."),
        ({"benta": None}, money.format("Benta")),
        ({"benta": -1}, money.format("Benta")),
        ({"benta": 10.5}, money.format("Benta")),
        ({"benta": "100"}, money.format("Benta")),
        ({"benta": True}, money.format("Benta")),
        ({"benta": 100_000_001}, money.format("Benta")),
        ({"puhunan": -5}, money.format("Puhunan")),
        ({"stock": -1}, count.format("Stock")),
        ({"stock": 1.5}, count.format("Stock")),
        ({"reorder_level": "2"}, count.format("Re-order")),
    ]
    for fields, message in cases:
        data = {"name": "OK", "benta": 100, "stock": 1, "reorder_level": 1, **fields}
        response = admin.post("/api/items", json=data)
        assert response.status_code == 400 and response.get_json()["error"] == message, fields
    assert items(admin.get("/api/items")) == []  # nothing was saved


def test_no_body_is_refused(admin):
    assert admin.post("/api/items").status_code == 400


def test_items_page_for_admin_and_staff(admin):
    page = admin.get("/items").get_data(as_text=True)
    assert "add-button" in page
    staff_page = login("staff1").get("/items")
    assert staff_page.status_code == 200
    assert "add-button" not in staff_page.get_data(as_text=True)


def test_items_page_needs_login(client):
    response = client.get("/items")
    assert response.status_code == 302 and response.headers["Location"].endswith("/login")
