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


def names(response):
    return [row["name"] for row in items(response)]


def test_search_matches_words_in_any_order_and_any_case(admin):
    make_item(admin, name="AIR FILTER SUNTAL", model="NMAX V1", part_no="YA040D")
    make_item(admin, name="AIR FILTER SUNTAL", model="MIO SOUL", part_no="YA040")
    make_item(admin, name="SPARK PLUG NGK", model="", part_no="C7HSA")
    assert len(items(admin.get("/api/items?q=air+nmax"))) == 1
    assert len(items(admin.get("/api/items?q=NMAX AIR"))) == 1
    assert len(items(admin.get("/api/items?q=air"))) == 2
    assert names(admin.get("/api/items?q=c7hsa")) == ["SPARK PLUG NGK"]
    assert items(admin.get("/api/items?q=nothing")) == []


def test_search_treats_percent_and_underscore_as_plain_text(admin):
    make_item(admin, name="OIL 10W-40")
    assert items(admin.get("/api/items?q=%25")) == []
    assert items(admin.get("/api/items?q=_")) == []
    make_item(admin, name="50% OFF TAPE")
    assert names(admin.get("/api/items?q=50%25")) == ["50% OFF TAPE"]


def test_blank_search_lists_everything(admin):
    make_item(admin)
    assert len(items(admin.get("/api/items?q=+++"))) == 1


def test_low_stock_filter(admin):
    make_item(admin, name="LOW ONE", stock=1, reorder_level=2)
    make_item(admin, name="EDGE", stock=2, reorder_level=2)
    make_item(admin, name="FINE", stock=9, reorder_level=2)
    make_item(admin, name="LINIS", track_stock=False)
    assert names(admin.get("/api/items?low=1")) == ["EDGE", "LOW ONE"]
    assert len(items(admin.get("/api/items"))) == 4


def test_pages(admin):
    add_items(120)
    first = admin.get("/api/items").get_json()
    assert first["total"] == 120 and first["pages"] == 3 and first["page"] == 1
    assert len(first["items"]) == 50 and first["items"][0]["name"] == "ITEM 001"
    last = admin.get("/api/items?page=3").get_json()
    assert len(last["items"]) == 20 and last["items"][-1]["name"] == "ITEM 120"
    assert admin.get("/api/items?page=99").get_json()["items"] == []
    assert admin.get("/api/items?page=0").get_json()["page"] == 1
    assert admin.get("/api/items?page=abc").get_json()["page"] == 1
    assert len(admin.get("/api/items?per_page=10").get_json()["items"]) == 10
    assert len(admin.get("/api/items?per_page=5000").get_json()["items"]) == 100  # capped


def test_search_and_low_stock_work_together_with_pages(admin):
    add_items(60)
    db_execute("UPDATE items SET stock = 1 WHERE name LIKE 'ITEM 05%'")
    data = admin.get("/api/items?q=item&low=1").get_json()
    assert data["total"] == 10 and data["pages"] == 1


def test_deactivated_items_are_hidden_for_staff_even_when_they_ask(admin):
    make_item(admin, name="KEEP")
    gone = make_item(admin, name="GONE")
    db_execute("UPDATE items SET active = 0 WHERE id = ?", (gone["id"],))
    staff = login("staff1")
    assert names(staff.get("/api/items")) == ["KEEP"]
    assert names(staff.get("/api/items?inactive=1")) == ["KEEP"]
    assert names(admin.get("/api/items")) == ["KEEP"]
    assert names(admin.get("/api/items?inactive=1")) == ["GONE", "KEEP"]


def test_seed_command_adds_sample_items_once(app, admin):
    runner = app.test_cli_runner()
    assert runner.invoke(args=["seed"]).exit_code == 0
    first = admin.get("/api/items?per_page=100").get_json()["total"]
    assert first >= 100
    assert runner.invoke(args=["seed"]).exit_code == 0
    assert admin.get("/api/items?per_page=100").get_json()["total"] == first


def test_edit_an_item(admin):
    item = make_item(admin)
    response = admin.put(f"/api/items/{item['id']}", json={
        "name": "  AIR FILTER  SUNTAL 2 ", "model": "NMAX V2", "part_no": "YA041",
        "puhunan": 11000, "benta": 16000, "reorder_level": 1, "track_stock": True})
    assert response.status_code == 200
    saved = response.get_json()["item"]
    assert saved["name"] == "AIR FILTER SUNTAL 2" and saved["model"] == "NMAX V2"
    assert saved["puhunan"] == 11000 and saved["benta"] == 16000 and saved["tubo"] == 5000
    assert saved["reorder_level"] == 1
    assert items(admin.get("/api/items"))[0]["name"] == "AIR FILTER SUNTAL 2"


def test_a_partial_edit_keeps_the_other_fields(admin):
    item = make_item(admin)
    saved = admin.put(f"/api/items/{item['id']}", json={"benta": 20000}).get_json()["item"]
    assert saved["benta"] == 20000
    assert saved["name"] == "AIR FILTER SUNTAL" and saved["puhunan"] == 10350 and saved["stock"] == 3


def test_edit_never_changes_the_stock(admin):
    item = make_item(admin, stock=3)
    saved = admin.put(f"/api/items/{item['id']}", json={"name": "NEW", "stock": 99}).get_json()["item"]
    assert saved["name"] == "NEW" and saved["stock"] == 3


def test_turning_stock_counting_off_keeps_the_number(admin):
    item = make_item(admin, stock=3, reorder_level=2)
    saved = admin.put(f"/api/items/{item['id']}", json={"track_stock": False}).get_json()["item"]
    assert saved["track_stock"] is False and saved["low_stock"] is False and saved["stock"] == 3
    again = admin.put(f"/api/items/{item['id']}", json={"track_stock": True}).get_json()["item"]
    assert again["stock"] == 3 and again["low_stock"] is False


def test_a_bad_edit_saves_nothing(admin):
    item = make_item(admin)
    assert admin.put(f"/api/items/{item['id']}", json={"name": "CHANGED", "benta": -5}).status_code == 400
    assert admin.put(f"/api/items/{item['id']}", json={"name": ""}).status_code == 400
    assert items(admin.get("/api/items"))[0]["name"] == "AIR FILTER SUNTAL"


def test_deactivate_and_activate(admin):
    item = make_item(admin)
    off = admin.put(f"/api/items/{item['id']}", json={"active": False}).get_json()["item"]
    assert off["active"] is False
    assert items(admin.get("/api/items")) == []
    assert len(items(admin.get("/api/items?inactive=1"))) == 1
    on = admin.put(f"/api/items/{item['id']}", json={"active": True}).get_json()["item"]
    assert on["active"] is True
    assert len(items(admin.get("/api/items"))) == 1


def test_unknown_item_is_not_found(admin):
    assert admin.put("/api/items/9999", json={"name": "x"}).status_code == 404


def test_staff_cannot_edit(admin):
    item = make_item(admin)
    staff = login("staff1")
    assert staff.put(f"/api/items/{item['id']}", json={"benta": 1}).status_code == 403
    assert items(admin.get("/api/items"))[0]["benta"] == 15000
