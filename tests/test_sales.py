"""Sales: recording a sale (feature A), listing the day (B) and voiding (C)."""

from datetime import timedelta

from conftest import db_query, login, make_item

from mymotoworks.config import shop_today


def today():
    return shop_today().isoformat()


def sell(client, lines, **extra):
    return client.post("/api/sales", json={"lines": lines, **extra})


def stock_of(admin, item):
    rows = admin.get("/api/items?per_page=100&inactive=1").get_json()["items"]
    return next(row["stock"] for row in rows if row["id"] == item["id"])


def sale_count():
    return db_query("SELECT COUNT(*) AS n FROM sales")[0]["n"]


def test_staff_sale_saves_the_total_lines_and_lowers_stock(admin):
    item = make_item(admin, stock=3)  # benta 15000, puhunan 10350
    staff = login("staff1")
    response = sell(staff, [{"item_id": item["id"], "qty": 2}])
    assert response.status_code == 201, response.get_json()
    sale = response.get_json()["sale"]
    assert sale["total"] == 30000 and sale["sale_date"] == today() and sale["voided"] is False
    assert sale["recorded_by"] == "Sample Staff"
    line = sale["lines"][0]
    assert line["name"] == "AIR FILTER SUNTAL" and line["qty"] == 2
    assert line["benta"] == 15000 and line["line_total"] == 30000
    assert stock_of(admin, item) == 1


def test_staff_never_see_cost_or_profit_in_a_sale(admin):
    item = make_item(admin)
    text = sell(login("staff1"), [{"item_id": item["id"], "qty": 1}]).get_data(as_text=True)
    assert "puhunan" not in text and "tubo" not in text


def test_admin_sees_cost_and_profit_in_a_sale(admin):
    item = make_item(admin)
    sale = sell(admin, [{"item_id": item["id"], "qty": 2}]).get_json()["sale"]
    assert sale["lines"][0]["puhunan"] == 10350 and sale["lines"][0]["tubo"] == (15000 - 10350) * 2
    assert sale["tubo"] == 9300


def test_a_changed_price_affects_only_that_line_and_is_remembered(admin):
    item = make_item(admin)
    sale = sell(login("staff1"), [{"item_id": item["id"], "qty": 2, "benta": 14000}]).get_json()["sale"]
    assert sale["total"] == 28000 and sale["lines"][0]["benta"] == 14000
    admin.put(f"/api/items/{item['id']}", json={"benta": 20000, "puhunan": 12000})
    row = db_query("SELECT benta, puhunan, item_name FROM sale_lines")[0]
    assert row == {"benta": 14000, "puhunan": 10350, "item_name": "AIR FILTER SUNTAL"}
    assert admin.get("/api/items").get_json()["items"][0]["benta"] == 20000


def test_a_price_of_zero_is_allowed(admin):
    item = make_item(admin)
    assert sell(admin, [{"item_id": item["id"], "qty": 1, "benta": 0}]).get_json()["sale"]["total"] == 0


def test_several_lines_add_up_and_each_item_loses_stock(admin):
    first, second = make_item(admin, stock=5), make_item(admin, name="SPARK PLUG", benta=9000, stock=4)
    sale = sell(admin, [{"item_id": first["id"], "qty": 1}, {"item_id": second["id"], "qty": 3}]).get_json()["sale"]
    assert sale["total"] == 15000 + 27000 and len(sale["lines"]) == 2
    assert stock_of(admin, first) == 4 and stock_of(admin, second) == 1


def test_the_same_item_on_two_lines_is_kept_as_two_lines(admin):
    item = make_item(admin, stock=5)
    sale = sell(admin, [{"item_id": item["id"], "qty": 1}, {"item_id": item["id"], "qty": 2, "benta": 100}]).get_json()["sale"]
    assert [line["qty"] for line in sale["lines"]] == [1, 2]
    assert stock_of(admin, item) == 2


def test_an_uncounted_item_never_changes_stock(admin):
    item = make_item(admin, name="LINIS", track_stock=False, stock=0)
    assert sell(admin, [{"item_id": item["id"], "qty": 4}]).status_code == 201
    assert stock_of(admin, item) == 0


def test_stock_may_go_below_zero(admin):
    item = make_item(admin, stock=1)
    assert sell(admin, [{"item_id": item["id"], "qty": 3}]).status_code == 201
    assert stock_of(admin, item) == -2


def test_one_bad_line_saves_nothing_and_lowers_no_stock(admin):
    good = make_item(admin, stock=5)
    gone = make_item(admin, name="GONE", stock=5)
    admin.put(f"/api/items/{gone['id']}", json={"active": False})
    for bad in ({"item_id": 9999, "qty": 1}, {"item_id": gone["id"], "qty": 1}, {"item_id": good["id"], "qty": 0}):
        response = sell(admin, [{"item_id": good["id"], "qty": 2}, bad])
        assert response.status_code == 400, bad
    assert stock_of(admin, good) == 5 and sale_count() == 0


def test_unavailable_item_messages(admin):
    gone = make_item(admin, name="OLD FILTER")
    admin.put(f"/api/items/{gone['id']}", json={"active": False})
    assert sell(admin, [{"item_id": gone["id"], "qty": 1}]).get_json()["error"] == "OLD FILTER is no longer for sale."
    assert sell(admin, [{"item_id": 9999, "qty": 1}]).get_json()["error"] == "An item in the cart does not exist."


def test_sale_rules(admin):
    item = make_item(admin)
    ok = {"item_id": item["id"], "qty": 1}
    qty = "Quantity must be a whole number from 1 to 1000."
    price = "Price must be an amount from 0 to 1,000,000 pesos."
    cases = [
        ({"lines": []}, "Add at least one item."),
        ({"lines": "x"}, "Add at least one item."),
        ({"lines": [ok] * 51}, "A sale can have at most 50 items."),
        ({"lines": ["x"]}, "Add at least one item."),
        ({"lines": [{**ok, "qty": 0}]}, qty),
        ({"lines": [{**ok, "qty": -1}]}, qty),
        ({"lines": [{**ok, "qty": 1.5}]}, qty),
        ({"lines": [{**ok, "qty": "2"}]}, qty),
        ({"lines": [{**ok, "qty": True}]}, qty),
        ({"lines": [{**ok, "qty": 1001}]}, qty),
        ({"lines": [{"qty": 1}]}, "An item in the cart does not exist."),
        ({"lines": [{**ok, "item_id": "1"}]}, "An item in the cart does not exist."),
        ({"lines": [{**ok, "item_id": True}]}, "An item in the cart does not exist."),
        ({"lines": [{**ok, "benta": -1}]}, price),
        ({"lines": [{**ok, "benta": 1.5}]}, price),
        ({"lines": [{**ok, "benta": "100"}]}, price),
        ({"lines": [ok], "client_ref": 123}, "That sale reference is not valid."),
        ({"lines": [ok], "client_ref": "x" * 65}, "That sale reference is not valid."),
    ]
    for body, message in cases:
        response = admin.post("/api/sales", json=body)
        assert response.status_code == 400 and response.get_json()["error"] == message, body
    assert sale_count() == 0 and stock_of(admin, item) == 3


def test_no_body_and_no_login(admin, client):
    assert admin.post("/api/sales").status_code == 400
    assert client.post("/api/sales", json={}).status_code == 401


def test_a_double_tap_with_the_same_reference_saves_once(admin):
    item = make_item(admin, stock=5)
    staff = login("staff1")
    body = [{"item_id": item["id"], "qty": 2}]
    first = sell(staff, body, client_ref="cart-1")
    second = sell(staff, body, client_ref="cart-1")
    assert first.status_code == 201 and second.status_code == 200
    assert second.get_json()["duplicate"] is True
    assert second.get_json()["sale"]["id"] == first.get_json()["sale"]["id"]
    assert sale_count() == 1 and stock_of(admin, item) == 3


def test_a_new_reference_is_a_new_sale(admin):
    item = make_item(admin, stock=5)
    staff = login("staff1")
    sell(staff, [{"item_id": item["id"], "qty": 1}], client_ref="cart-1")
    assert sell(staff, [{"item_id": item["id"], "qty": 1}], client_ref="cart-2").status_code == 201
    assert sale_count() == 2


def test_staff_can_only_sell_today(admin):
    item = make_item(admin)
    staff = login("staff1")
    line = [{"item_id": item["id"], "qty": 1}]
    assert sell(staff, line, sale_date=today()).status_code == 201
    yesterday = (shop_today() - timedelta(days=1)).isoformat()
    response = sell(staff, line, sale_date=yesterday)
    assert response.status_code == 400 and response.get_json()["error"] == "Staff can only record today's sales."


def test_admin_can_back_date_but_not_future_date(admin):
    item = make_item(admin, stock=9)
    line = [{"item_id": item["id"], "qty": 1}]
    yesterday = (shop_today() - timedelta(days=1)).isoformat()
    tomorrow = (shop_today() + timedelta(days=1)).isoformat()
    assert sell(admin, line, sale_date=yesterday).get_json()["sale"]["sale_date"] == yesterday
    response = sell(admin, line, sale_date=tomorrow)
    assert response.status_code == 400 and response.get_json()["error"] == "The date can't be in the future."


def test_bad_dates_are_refused(admin):
    item = make_item(admin)
    line = [{"item_id": item["id"], "qty": 1}]
    for bad in ("10/16/2026", "2026-13-40", "20261016", 20261016, "tomorrow", [], "2026-1-5"):
        response = sell(admin, line, sale_date=bad)
        assert response.status_code == 400, bad
        assert response.get_json()["error"] == "Date must look like 2026-10-16.", bad
    assert sale_count() == 0


def test_a_missing_or_empty_date_means_today(admin):
    item = make_item(admin, stock=9)
    line = [{"item_id": item["id"], "qty": 1}]
    assert sell(admin, line).get_json()["sale"]["sale_date"] == today()
    assert sell(admin, line, sale_date="").get_json()["sale"]["sale_date"] == today()
    assert sell(admin, line, sale_date=None).get_json()["sale"]["sale_date"] == today()


def test_sell_page_for_staff_and_admin(admin, client):
    staff_page = login("staff1").get("/sell")
    assert staff_page.status_code == 200
    assert 'id="sale-date"' not in staff_page.get_data(as_text=True)
    assert 'id="sale-date"' in admin.get("/sell").get_data(as_text=True)
    assert client.get("/sell").status_code == 302


def test_staff_land_on_the_sell_page_after_login(client):
    response = client.post("/api/login", json={"username": "staff1", "password": "1234"})
    assert response.get_json()["home"] == "/sell"
    admin_login = client.post("/api/login", json={"username": "admin", "password": "admin"})
    assert admin_login.get_json()["home"] == "/dashboard"
