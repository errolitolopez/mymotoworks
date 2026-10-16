"""Restocks: recording one (feature A), the history (B) and voiding (C)."""

from datetime import timedelta

from conftest import db_query, login, make_item

from mymotoworks.config import shop_today


def today():
    return shop_today().isoformat()


def restock(client, lines, **extra):
    return client.post("/api/restocks", json={"lines": lines, **extra})


def item_row(admin, item):
    rows = admin.get("/api/items/all").get_json()["items"]
    return next(row for row in rows if row["id"] == item["id"])


def sale_costs():
    return [row["puhunan"] for row in db_query("SELECT puhunan FROM sale_lines ORDER BY id")]


def sold(admin, item, qty=1):
    """An approved sale of the item (its puhunan is copied onto the sale line)."""
    sale = admin.post("/api/sales", json={"lines": [{"item_id": item["id"], "qty": qty}]}).get_json()["sale"]
    assert admin.post(f"/api/sales/{sale['id']}/approve").status_code == 200


def test_restock_raises_the_stock_and_sets_the_new_cost(admin):
    item = make_item(admin, stock=3)  # puhunan 10350
    response = restock(admin, [{"item_id": item["id"], "qty": 10, "puhunan": 11000}], note="  Supplier   Ben ")
    assert response.status_code == 201, response.get_json()
    saved = response.get_json()["restock"]
    assert saved["total"] == 110000 and saved["restock_date"] == today() and saved["voided"] is False
    assert saved["note"] == "Supplier Ben" and saved["recorded_by"] == "Administrator"
    line = saved["lines"][0]
    assert line["qty"] == 10 and line["puhunan"] == 11000 and line["old_puhunan"] == 10350
    assert line["line_total"] == 110000 and line["name"] == "AIR FILTER SUNTAL"
    now = item_row(admin, item)
    assert now["stock"] == 13 and now["puhunan"] == 11000


def test_a_cost_left_out_keeps_the_current_one(admin):
    item = make_item(admin, stock=3)
    saved = restock(admin, [{"item_id": item["id"], "qty": 5}]).get_json()["restock"]
    assert saved["lines"][0]["puhunan"] == 10350 and saved["total"] == 51750
    assert item_row(admin, item)["puhunan"] == 10350 and item_row(admin, item)["stock"] == 8


def test_a_cost_of_zero_is_allowed(admin):
    item = make_item(admin, stock=0)
    assert restock(admin, [{"item_id": item["id"], "qty": 2, "puhunan": 0}]).status_code == 201
    assert item_row(admin, item)["puhunan"] == 0


def test_several_items_in_one_restock(admin):
    first, second = make_item(admin, stock=1), make_item(admin, name="SPARK PLUG", puhunan=5000, benta=9000, stock=0)
    saved = restock(admin, [{"item_id": first["id"], "qty": 2, "puhunan": 10000},
                            {"item_id": second["id"], "qty": 4, "puhunan": 5500}]).get_json()["restock"]
    assert saved["total"] == 2 * 10000 + 4 * 5500
    assert item_row(admin, first)["stock"] == 3 and item_row(admin, second)["stock"] == 4


def test_old_sales_keep_the_old_cost_and_new_sales_use_the_new_one(admin):
    item = make_item(admin, stock=5)  # puhunan 10350
    sold(admin, item)
    restock(admin, [{"item_id": item["id"], "qty": 5, "puhunan": 12000}])
    sold(admin, item)
    assert sale_costs() == [10350, 12000]


def test_staff_cannot_restock_and_visitors_are_refused(admin, client):
    item = make_item(admin, stock=3)
    staff = login("staff1")
    assert restock(staff, [{"item_id": item["id"], "qty": 1}]).status_code == 403
    assert client.post("/api/restocks", json={}).status_code == 401
    assert item_row(admin, item)["stock"] == 3
    assert staff.get("/restock").status_code == 302
    assert client.get("/restock").status_code == 302


def test_the_same_item_twice_is_refused(admin):
    item = make_item(admin, stock=3)
    line = {"item_id": item["id"], "qty": 1}
    response = restock(admin, [line, line])
    assert response.status_code == 400 and response.get_json()["error"] == "An item is listed twice."
    assert item_row(admin, item)["stock"] == 3


def test_items_that_cannot_be_restocked(admin):
    gone = make_item(admin, name="OLD FILTER")
    admin.put(f"/api/items/{gone['id']}", json={"active": False})
    loose = make_item(admin, name="LINIS", track_stock=False)
    cases = [
        ({"item_id": gone["id"], "qty": 1}, "OLD FILTER is no longer for sale."),
        ({"item_id": loose["id"], "qty": 1}, "LINIS does not count stock, so it cannot be restocked."),
        ({"item_id": 9999, "qty": 1}, "An item in the list does not exist."),
    ]
    for line, message in cases:
        response = restock(admin, [line])
        assert response.status_code == 400 and response.get_json()["error"] == message, line


def test_one_bad_line_saves_nothing_and_changes_no_stock_or_cost(admin):
    good = make_item(admin, stock=3)
    for bad in ({"item_id": 9999, "qty": 1}, {"item_id": good["id"] + 1000, "qty": 1}):
        response = restock(admin, [{"item_id": good["id"], "qty": 5, "puhunan": 99999}, bad])
        assert response.status_code == 400, bad
    now = item_row(admin, good)
    assert now["stock"] == 3 and now["puhunan"] == 10350
    assert db_query("SELECT COUNT(*) AS n FROM restocks")[0]["n"] == 0


def test_restock_rules(admin):
    item = make_item(admin, stock=3)
    ok = {"item_id": item["id"], "qty": 1}
    qty = "Quantity must be a whole number from 1 to 100000."
    cost = "Cost must be an amount from 0 to 1,000,000 pesos."
    does_not_exist = "An item in the list does not exist."
    cases = [
        ({"lines": []}, "Add at least one item."),
        ({"lines": "x"}, "Add at least one item."),
        ({"lines": ["x"]}, "Add at least one item."),
        ({"lines": [{**ok, "item_id": n} for n in range(1, 102)]}, "A restock can have at most 100 items."),
        ({"lines": [{**ok, "qty": 0}]}, qty),
        ({"lines": [{**ok, "qty": -1}]}, qty),
        ({"lines": [{**ok, "qty": 1.5}]}, qty),
        ({"lines": [{**ok, "qty": "2"}]}, qty),
        ({"lines": [{**ok, "qty": True}]}, qty),
        ({"lines": [{**ok, "qty": 100001}]}, qty),
        ({"lines": [{"qty": 1}]}, does_not_exist),
        ({"lines": [{**ok, "item_id": "1"}]}, does_not_exist),
        ({"lines": [{**ok, "item_id": True}]}, does_not_exist),
        ({"lines": [{**ok, "puhunan": -1}]}, cost),
        ({"lines": [{**ok, "puhunan": 1.5}]}, cost),
        ({"lines": [{**ok, "puhunan": "100"}]}, cost),
        ({"lines": [ok], "note": "x" * 201}, "Note can be at most 200 characters."),
        ({"lines": [ok], "note": 123}, "Note must be text."),
        ({"lines": [ok], "client_ref": 5}, "That restock reference is not valid."),
        ({"lines": [ok], "client_ref": "x" * 65}, "That restock reference is not valid."),
        ({"lines": [ok], "restock_date": "10/16/2026"}, "Date must look like 2026-10-16."),
        ({"lines": [ok], "restock_date": 20261016}, "Date must look like 2026-10-16."),
    ]
    for body, message in cases:
        response = admin.post("/api/restocks", json=body)
        assert response.status_code == 400 and response.get_json()["error"] == message, body
    assert item_row(admin, item)["stock"] == 3
    assert db_query("SELECT COUNT(*) AS n FROM restocks")[0]["n"] == 0


def test_no_body_is_refused(admin):
    assert admin.post("/api/restocks").status_code == 400


def test_dates(admin):
    item = make_item(admin, stock=0)
    line = [{"item_id": item["id"], "qty": 1}]
    yesterday = (shop_today() - timedelta(days=1)).isoformat()
    tomorrow = (shop_today() + timedelta(days=1)).isoformat()
    assert restock(admin, line, restock_date=yesterday).get_json()["restock"]["restock_date"] == yesterday
    assert restock(admin, line, restock_date="").get_json()["restock"]["restock_date"] == today()
    assert restock(admin, line, restock_date=None).get_json()["restock"]["restock_date"] == today()
    response = restock(admin, line, restock_date=tomorrow)
    assert response.status_code == 400 and response.get_json()["error"] == "The date can't be in the future."


def test_a_double_tap_with_the_same_reference_saves_once(admin):
    item = make_item(admin, stock=3)
    line = [{"item_id": item["id"], "qty": 4, "puhunan": 11000}]
    first = restock(admin, line, client_ref="r-1")
    second = restock(admin, line, client_ref="r-1")
    assert first.status_code == 201 and second.status_code == 200 and second.get_json()["duplicate"] is True
    assert second.get_json()["restock"]["id"] == first.get_json()["restock"]["id"]
    assert item_row(admin, item)["stock"] == 7
    assert db_query("SELECT COUNT(*) AS n FROM restocks")[0]["n"] == 1


def test_restock_pages_are_for_the_admin_only(admin, client):
    assert admin.get("/restock").status_code == 200
    html = admin.get("/restock").get_data(as_text=True)
    for element in ('id="item-filter"', 'id="item-list"', 'id="tab-items"', 'id="tab-cart"', 'id="restock-note"',
                    'id="restock-date"', 'id="save-restock"'):
        assert element in html, element
