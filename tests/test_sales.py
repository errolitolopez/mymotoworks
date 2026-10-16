"""Sales: recording a sale (feature A), listing the day (B) and voiding (C)."""

from datetime import timedelta

from conftest import db_execute, db_query, login, make_item

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


def test_staff_sale_saves_the_total_and_lines_but_waits_for_approval(admin):
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
    assert sale["status"] == "pending"
    assert stock_of(admin, item) == 3  # a pending sale does not touch the stock


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
    assert sale_count() == 1 and stock_of(admin, item) == 5  # pending: stock untouched


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


def day(client, date=None):
    url = "/api/sales" + (f"?date={date}" if date else "")
    return client.get(url)


def test_the_day_lists_sales_newest_first_with_totals(admin):
    item = make_item(admin, stock=9)
    staff = login("staff1")
    first = sell(staff, [{"item_id": item["id"], "qty": 1}]).get_json()["sale"]
    second = sell(admin, [{"item_id": item["id"], "qty": 2}]).get_json()["sale"]
    data = day(staff).get_json()
    assert data["date"] == today()
    assert [sale["id"] for sale in data["sales"]] == [second["id"], first["id"]]
    # The staff sale is pending, so only the admin's own (approved) sale is in the totals.
    assert data["summary"]["count"] == 1 and data["summary"]["total"] == 30000
    assert data["summary"]["pending"] == {"count": 1, "total": 15000}
    assert data["sales"][0]["lines"][0]["qty"] == 2


def test_staff_see_the_day_without_cost_or_profit(admin):
    item = make_item(admin, stock=9)
    sell(admin, [{"item_id": item["id"], "qty": 1}])
    text = day(login("staff1")).get_data(as_text=True)
    assert "AIR FILTER SUNTAL" in text and "puhunan" not in text and "tubo" not in text


def test_admin_sees_the_day_tubo(admin):
    item = make_item(admin, stock=9)
    sell(admin, [{"item_id": item["id"], "qty": 2}])
    data = day(admin).get_json()
    assert data["summary"]["tubo"] == 9300 and data["sales"][0]["tubo"] == 9300


def test_staff_can_only_read_today(admin):
    yesterday = (shop_today() - timedelta(days=1)).isoformat()
    response = day(login("staff1"), yesterday)
    assert response.status_code == 403
    assert response.get_json()["error"] == "You can only see today's sales."
    assert day(login("staff1"), today()).status_code == 200


def test_admin_reads_any_day_and_sales_stay_on_their_own_day(admin):
    item = make_item(admin, stock=9)
    yesterday = (shop_today() - timedelta(days=1)).isoformat()
    sell(admin, [{"item_id": item["id"], "qty": 1}], sale_date=yesterday)
    assert day(admin).get_json()["summary"]["count"] == 0
    assert day(admin, yesterday).get_json()["summary"]["count"] == 1
    assert day(admin, "2020-01-01").get_json() == {
        "date": "2020-01-01", "sales": [],
        "summary": {"count": 0, "total": 0, "tubo": 0, "pending": {"count": 0, "total": 0}}}


def test_bad_day_is_refused(admin):
    for bad in ("x", "2026-13-40", "20261016"):
        response = day(admin, bad)
        assert response.status_code == 400 and response.get_json()["error"] == "Date must look like 2026-10-16."


def test_the_time_is_shown_in_shop_time(admin):
    item = make_item(admin)
    sale = sell(admin, [{"item_id": item["id"], "qty": 1}]).get_json()["sale"]
    db_execute("UPDATE sales SET created_at = '2026-10-16 02:30:00' WHERE id = ?", (sale["id"],))
    assert day(admin).get_json()["sales"][0]["recorded_at"] == "10:30"  # UTC+8


def test_sales_page_and_tabs(admin, client):
    assert login("staff1").get("/sales").status_code == 200
    html = admin.get("/sales").get_data(as_text=True)
    assert 'id="day-date"' in html
    assert 'id="day-date"' not in login("staff1").get("/sales").get_data(as_text=True)
    assert client.get("/sales").status_code == 302
    assert client.get("/api/sales").status_code == 401


def void(client, sale_id, reason="Wrong item"):
    return client.post(f"/api/sales/{sale_id}/void", json={"reason": reason})


def test_void_puts_the_stock_back_and_leaves_the_totals(admin):
    item = make_item(admin, stock=5)
    sale = sell(admin, [{"item_id": item["id"], "qty": 3}]).get_json()["sale"]
    assert stock_of(admin, item) == 2
    response = void(admin, sale["id"], "  Customer changed mind ")
    assert response.status_code == 200
    voided = response.get_json()["sale"]
    assert voided["voided"] is True and voided["void_reason"] == "Customer changed mind"
    assert stock_of(admin, item) == 5
    data = day(admin).get_json()
    assert data["summary"] == {"count": 0, "total": 0, "tubo": 0, "pending": {"count": 0, "total": 0}}
    assert data["sales"][0]["voided"] is True  # still listed, struck through on the page
    assert db_query("SELECT voided_by FROM sales")[0]["voided_by"] is not None


def test_staff_cannot_void(admin):
    item = make_item(admin, stock=5)
    staff = login("staff1")
    sale = sell(staff, [{"item_id": item["id"], "qty": 1}]).get_json()["sale"]
    assert void(staff, sale["id"]).status_code == 403
    assert stock_of(admin, item) == 5  # pending: never touched


def test_voiding_twice_puts_stock_back_only_once(admin):
    item = make_item(admin, stock=5)
    sale = sell(admin, [{"item_id": item["id"], "qty": 2}]).get_json()["sale"]
    assert void(admin, sale["id"]).status_code == 200
    again = void(admin, sale["id"])
    assert again.status_code == 400 and again.get_json()["error"] == "This sale is already voided."
    assert stock_of(admin, item) == 5


def test_void_restores_exactly_what_the_sale_took(admin):
    counted = make_item(admin, stock=5)
    loose = make_item(admin, name="LINIS", track_stock=False)
    sale = sell(admin, [{"item_id": counted["id"], "qty": 2}, {"item_id": loose["id"], "qty": 3}]).get_json()["sale"]
    # The counted item stops counting stock after the sale; the void must still put its 2 back.
    admin.put(f"/api/items/{counted['id']}", json={"track_stock": False})
    admin.put(f"/api/items/{loose['id']}", json={"track_stock": True})
    void(admin, sale["id"])
    assert stock_of(admin, counted) == 5  # 5 - 2 + 2
    assert stock_of(admin, loose) == 0    # the loose item never lost stock, so none comes back


def test_void_of_a_sale_with_a_deactivated_item_still_works(admin):
    item = make_item(admin, stock=5)
    sale = sell(admin, [{"item_id": item["id"], "qty": 2}]).get_json()["sale"]
    admin.put(f"/api/items/{item['id']}", json={"active": False})
    assert void(admin, sale["id"]).status_code == 200
    assert stock_of(admin, item) == 5


def test_void_needs_a_reason(admin):
    item = make_item(admin)
    sale = sell(admin, [{"item_id": item["id"], "qty": 1}]).get_json()["sale"]
    for bad in ("", "   ", None, 5, "x" * 201):
        response = admin.post(f"/api/sales/{sale['id']}/void", json={"reason": bad})
        assert response.status_code == 400, bad
    assert admin.post(f"/api/sales/{sale['id']}/void").status_code == 400
    assert day(admin).get_json()["summary"]["count"] == 1


def test_void_of_an_unknown_sale_is_not_found(admin):
    assert void(admin, 9999).status_code == 404


def test_a_voided_sale_with_the_same_cart_reference_is_not_saved_again(admin):
    item = make_item(admin, stock=5)
    body = [{"item_id": item["id"], "qty": 1}]
    first = sell(admin, body, client_ref="cart-1").get_json()["sale"]
    void(admin, first["id"])
    again = sell(admin, body, client_ref="cart-1")
    assert again.status_code == 200 and again.get_json()["duplicate"] is True
    assert again.get_json()["sale"]["voided"] is True
    assert stock_of(admin, item) == 5


def test_void_form_is_only_on_the_admin_sales_page(admin):
    assert 'id="void-modal"' in admin.get("/sales").get_data(as_text=True)
    assert 'id="void-modal"' not in login("staff1").get("/sales").get_data(as_text=True)


def test_a_note_is_saved_trimmed_and_shown_in_the_day(admin):
    item = make_item(admin, stock=9)
    sale = sell(login("staff1"), [{"item_id": item["id"], "qty": 1}], note="  Mang   Ben  (tricycle) ").get_json()["sale"]
    assert sale["note"] == "Mang Ben (tricycle)"
    assert day(admin).get_json()["sales"][0]["note"] == "Mang Ben (tricycle)"


def test_the_note_is_optional(admin):
    item = make_item(admin, stock=9)
    line = [{"item_id": item["id"], "qty": 1}]
    assert sell(admin, line).get_json()["sale"]["note"] == ""
    assert sell(admin, line, note=None).get_json()["sale"]["note"] == ""
    assert sell(admin, line, note="   ").get_json()["sale"]["note"] == ""


def test_note_rules(admin):
    item = make_item(admin, stock=9)
    line = [{"item_id": item["id"], "qty": 1}]
    long = sell(admin, line, note="x" * 101)
    assert long.status_code == 400 and long.get_json()["error"] == "Note can be at most 100 characters."
    assert sell(admin, line, note="x" * 100).status_code == 201
    for bad in (123, ["Ben"], True, {"a": 1}):
        response = sell(admin, line, note=bad)
        assert response.status_code == 400 and response.get_json()["error"] == "Note must be text.", bad


def test_a_note_with_html_is_kept_as_plain_text(admin):
    item = make_item(admin, stock=9)
    sale = sell(admin, [{"item_id": item["id"], "qty": 1}], note="<b>Ben</b> & co").get_json()["sale"]
    assert sale["note"] == "<b>Ben</b> & co"  # the page shows it with textContent, never as HTML


def test_the_note_survives_a_duplicate_tap(admin):
    item = make_item(admin, stock=9)
    line = [{"item_id": item["id"], "qty": 1}]
    sell(admin, line, client_ref="r1", note="Ben")
    again = sell(admin, line, client_ref="r1", note="Ben")
    assert again.get_json()["duplicate"] is True and again.get_json()["sale"]["note"] == "Ben"


def test_the_sell_page_has_a_note_box(admin):
    assert 'id="sale-note"' in admin.get("/sell").get_data(as_text=True)
    assert 'id="sale-note"' in login("staff1").get("/sell").get_data(as_text=True)


def test_an_old_database_without_the_note_column_is_upgraded_and_keeps_its_sales(tmp_path):
    import sqlite3
    from mymotoworks import create_app

    path = str(tmp_path / "old.db")
    old = sqlite3.connect(path)
    # A real older database always has its users, and the sales point at them.
    old.execute("CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, "
                "username TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL, "
                "role TEXT NOT NULL CHECK (role IN ('admin', 'staff')), "
                "must_change_password INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1, "
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    old.execute("INSERT INTO users (name, username, password_hash, role) VALUES ('Administrator', 'admin', 'x', 'admin')")
    old.execute("CREATE TABLE sales (id INTEGER PRIMARY KEY AUTOINCREMENT, sale_date TEXT NOT NULL, "
                "user_id INTEGER NOT NULL, total INTEGER NOT NULL, client_ref TEXT UNIQUE, voided_at TEXT, "
                "voided_by INTEGER, void_reason TEXT NOT NULL DEFAULT '', "
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    old.execute("INSERT INTO sales (sale_date, user_id, total) VALUES ('2026-10-16', 1, 500)")
    old.commit()
    old.close()
    for _ in range(2):  # starting twice must not fail
        create_app({"DATABASE": path})
    upgraded = sqlite3.connect(path)
    assert upgraded.execute("SELECT total, note, replaces_sale_id FROM sales").fetchall() == [(500, "", None)]
    upgraded.close()


def copy_of(client, sale_id):
    return client.get(f"/api/sales/{sale_id}/copy")


def test_copy_gives_the_items_prices_and_note_and_changes_nothing(admin):
    item = make_item(admin, stock=9)
    staff = login("staff1")
    sale = sell(staff, [{"item_id": item["id"], "qty": 2, "benta": 14000}], note="Mang Ben").get_json()["sale"]
    admin.put(f"/api/items/{item['id']}", json={"benta": 20000})  # the price changes later
    data = copy_of(staff, sale["id"]).get_json()
    assert data["sale_id"] == sale["id"] and data["note"] == "Mang Ben" and data["voided"] is False
    assert data["sale_date"] == today() and data["skipped"] == []
    line = data["lines"][0]
    assert line["qty"] == 2 and line["benta"] == 14000          # what was charged, not the new price
    assert line["item"]["id"] == item["id"] and line["item"]["benta"] == 20000
    assert "puhunan" not in copy_of(staff, sale["id"]).get_data(as_text=True)
    assert sale_count() == 1 and stock_of(admin, item) == 9  # the staff sale is pending: stock untouched


def test_copy_leaves_out_items_that_are_no_longer_for_sale(admin):
    keep, gone = make_item(admin, stock=9), make_item(admin, name="OLD FILTER", stock=9)
    sale = sell(admin, [{"item_id": keep["id"], "qty": 1}, {"item_id": gone["id"], "qty": 1}]).get_json()["sale"]
    admin.put(f"/api/items/{gone['id']}", json={"active": False})
    data = copy_of(admin, sale["id"]).get_json()
    assert [line["item"]["id"] for line in data["lines"]] == [keep["id"]]
    assert data["skipped"] == ["OLD FILTER is no longer for sale."]


def test_staff_can_copy_only_todays_sales_and_admin_any(admin, client):
    item = make_item(admin, stock=9)
    yesterday = (shop_today() - timedelta(days=1)).isoformat()
    old = sell(admin, [{"item_id": item["id"], "qty": 1}], sale_date=yesterday).get_json()["sale"]
    response = copy_of(login("staff1"), old["id"])
    assert response.status_code == 403 and response.get_json()["error"] == "You can only see today's sales."
    assert copy_of(admin, old["id"]).status_code == 200
    assert copy_of(admin, 9999).status_code == 404
    assert copy_of(client, old["id"]).status_code == 401


def test_a_voided_sale_can_still_be_copied(admin):
    item = make_item(admin, stock=9)
    sale = sell(admin, [{"item_id": item["id"], "qty": 1}]).get_json()["sale"]
    void(admin, sale["id"])
    data = copy_of(login("staff1"), sale["id"]).get_json()
    assert data["voided"] is True and len(data["lines"]) == 1


def test_replace_voids_the_old_sale_and_keeps_both_records(admin):
    item = make_item(admin, stock=5)
    old = sell(admin, [{"item_id": item["id"], "qty": 3}], note="Ben").get_json()["sale"]
    assert stock_of(admin, item) == 2
    response = sell(admin, [{"item_id": item["id"], "qty": 2}], note="Ben", replaces=old["id"])
    assert response.status_code == 201, response.get_json()
    new = response.get_json()["sale"]
    assert new["replaces"] == old["id"] and new["total"] == 30000
    assert stock_of(admin, item) == 3                      # 5 - 3 + 3 - 2
    listed = {sale["id"]: sale for sale in day(admin).get_json()["sales"]}
    assert set(listed) == {old["id"], new["id"]}
    kept = listed[old["id"]]                               # the old record is untouched
    assert kept["voided"] is True and kept["void_reason"] == f"Replaced by sale #{new['id']}"
    assert kept["replaced_by"] == new["id"] and kept["total"] == 45000 and kept["note"] == "Ben"
    assert kept["lines"][0]["qty"] == 3 and kept["lines"][0]["benta"] == 15000
    summary = day(admin).get_json()["summary"]
    assert summary["count"] == 1 and summary["total"] == 30000


def test_a_replacement_takes_the_old_sales_date(admin):
    item = make_item(admin, stock=9)
    yesterday = (shop_today() - timedelta(days=1)).isoformat()
    old = sell(admin, [{"item_id": item["id"], "qty": 1}], sale_date=yesterday).get_json()["sale"]
    new = sell(admin, [{"item_id": item["id"], "qty": 2}], sale_date=today(), replaces=old["id"]).get_json()["sale"]
    assert new["sale_date"] == yesterday
    assert day(admin, today()).get_json()["summary"]["count"] == 0
    assert day(admin, yesterday).get_json()["summary"]["count"] == 1


def test_only_the_admin_can_replace(admin):
    item = make_item(admin, stock=5)
    staff = login("staff1")
    old = sell(staff, [{"item_id": item["id"], "qty": 1}]).get_json()["sale"]
    response = sell(staff, [{"item_id": item["id"], "qty": 1}], replaces=old["id"])
    assert response.status_code == 403 and response.get_json()["error"] == "Only the admin can replace a sale."
    assert sale_count() == 1 and stock_of(admin, item) == 5
    assert day(admin).get_json()["sales"][0]["voided"] is False


def test_replace_rules_and_nothing_is_saved_on_failure(admin):
    item = make_item(admin, stock=5)
    old = sell(admin, [{"item_id": item["id"], "qty": 1}]).get_json()["sale"]
    line = [{"item_id": item["id"], "qty": 1}]
    assert sell(admin, line, replaces=9999).status_code == 404
    for bad in ("1", True, 0, -1, 1.5, [1]):
        response = sell(admin, line, replaces=bad)
        assert response.status_code == 400 and response.get_json()["error"] == "Sale to replace is not valid.", bad
    gone = make_item(admin, name="GONE", stock=5)
    admin.put(f"/api/items/{gone['id']}", json={"active": False})
    failed = sell(admin, [{"item_id": gone["id"], "qty": 1}], replaces=old["id"])
    assert failed.status_code == 400
    assert sale_count() == 1 and stock_of(admin, item) == 4
    assert day(admin).get_json()["sales"][0]["voided"] is False


def test_an_already_voided_sale_cannot_be_replaced(admin):
    item = make_item(admin, stock=5)
    old = sell(admin, [{"item_id": item["id"], "qty": 1}]).get_json()["sale"]
    void(admin, old["id"])
    response = sell(admin, [{"item_id": item["id"], "qty": 1}], replaces=old["id"])
    assert response.status_code == 400 and response.get_json()["error"] == "That sale is already voided."
    assert sale_count() == 1 and stock_of(admin, item) == 5


def test_a_replacement_sale_cannot_be_replaced_twice_by_a_double_tap(admin):
    item = make_item(admin, stock=5)
    old = sell(admin, [{"item_id": item["id"], "qty": 1}]).get_json()["sale"]
    line = [{"item_id": item["id"], "qty": 2}]
    first = sell(admin, line, replaces=old["id"], client_ref="fix-1")
    second = sell(admin, line, replaces=old["id"], client_ref="fix-1")
    assert first.status_code == 201 and second.status_code == 200 and second.get_json()["duplicate"] is True
    assert sale_count() == 2 and stock_of(admin, item) == 3


def test_a_replacement_can_itself_be_voided_later(admin):
    item = make_item(admin, stock=5)
    old = sell(admin, [{"item_id": item["id"], "qty": 1}]).get_json()["sale"]
    new = sell(admin, [{"item_id": item["id"], "qty": 2}], replaces=old["id"]).get_json()["sale"]
    assert void(admin, new["id"]).status_code == 200
    # 5, sold 1 -> 4, replaced by 2 -> 3, the replacement voided -> 5. The old sale stays voided.
    assert stock_of(admin, item) == 5
    assert day(admin).get_json()["summary"]["count"] == 0


def test_the_sell_page_has_the_replace_box_for_the_admin_only(admin):
    assert 'id="replace-box"' in admin.get("/sell?copy=1").get_data(as_text=True)
    assert 'id="replace-box"' not in login("staff1").get("/sell?copy=1").get_data(as_text=True)
    assert 'id="copy-banner"' in login("staff1").get("/sell").get_data(as_text=True)


def pending_sale(admin, qty=2, **fields):
    """A staff sale (pending) of a fresh item with stock 5. Returns (item, sale)."""
    item = make_item(admin, stock=5, **fields)
    sale = sell(login("staff1"), [{"item_id": item["id"], "qty": qty}]).get_json()["sale"]
    return item, sale


def approve(client, sale_id):
    return client.post(f"/api/sales/{sale_id}/approve")


def test_the_admins_own_sale_is_approved_at_once_and_staff_sale_is_pending(admin):
    item = make_item(admin, stock=5)
    mine = sell(admin, [{"item_id": item["id"], "qty": 1}]).get_json()["sale"]
    theirs = sell(login("staff1"), [{"item_id": item["id"], "qty": 1}]).get_json()["sale"]
    assert mine["status"] == "approved" and theirs["status"] == "pending"
    assert stock_of(admin, item) == 4  # only the admin's sale took stock


def test_pending_sales_stay_out_of_the_totals_but_are_shown_apart(admin):
    item, sale = pending_sale(admin, qty=2)
    data = day(admin).get_json()
    assert data["summary"] == {"count": 0, "total": 0, "tubo": 0, "pending": {"count": 1, "total": 30000}}
    assert data["sales"][0]["status"] == "pending"
    staff_summary = day(login("staff1")).get_json()["summary"]
    assert staff_summary == {"count": 0, "total": 0, "pending": {"count": 1, "total": 30000}}


def test_approving_lowers_the_stock_and_counts_the_sale(admin):
    item, sale = pending_sale(admin, qty=2)
    response = approve(admin, sale["id"])
    assert response.status_code == 200 and response.get_json()["sale"]["status"] == "approved"
    assert stock_of(admin, item) == 3
    data = day(admin).get_json()
    assert data["summary"]["count"] == 1 and data["summary"]["total"] == 30000
    assert data["summary"]["tubo"] == 9300 and data["summary"]["pending"] == {"count": 0, "total": 0}


def test_approving_may_take_stock_below_zero(admin):
    item = make_item(admin, stock=1)
    sale = sell(login("staff1"), [{"item_id": item["id"], "qty": 3}]).get_json()["sale"]
    approve(admin, sale["id"])
    assert stock_of(admin, item) == -2


def test_approving_an_uncounted_item_never_changes_stock(admin):
    item = make_item(admin, name="LINIS", track_stock=False)
    sale = sell(login("staff1"), [{"item_id": item["id"], "qty": 3}]).get_json()["sale"]
    approve(admin, sale["id"])
    assert stock_of(admin, item) == 0


def test_staff_cannot_approve_and_nothing_changes(admin):
    item, sale = pending_sale(admin)
    assert approve(login("staff1"), sale["id"]).status_code == 403
    assert stock_of(admin, item) == 5 and day(admin).get_json()["sales"][0]["status"] == "pending"


def test_approving_twice_or_a_voided_or_unknown_sale_is_refused(admin):
    item, sale = pending_sale(admin)
    assert approve(admin, sale["id"]).status_code == 200
    again = approve(admin, sale["id"])
    assert again.status_code == 400 and again.get_json()["error"] == "This sale is already approved."
    assert stock_of(admin, item) == 3
    other_item, other = pending_sale(admin)
    void(admin, other["id"], "Not real")
    refused = approve(admin, other["id"])
    assert refused.status_code == 400 and refused.get_json()["error"] == "This sale was voided."
    assert stock_of(admin, other_item) == 5
    assert approve(admin, 9999).status_code == 404


def test_rejecting_a_pending_sale_never_touches_the_stock(admin):
    item, sale = pending_sale(admin, qty=2)
    response = void(admin, sale["id"], "Wrong customer")
    assert response.status_code == 200 and response.get_json()["sale"]["status"] == "rejected"
    assert stock_of(admin, item) == 5  # nothing was taken, so nothing comes back
    data = day(admin).get_json()
    assert data["summary"]["pending"] == {"count": 0, "total": 0} and data["summary"]["count"] == 0
    assert data["sales"][0]["status"] == "rejected"
    assert approve(admin, sale["id"]).status_code == 400


def test_voiding_an_approved_sale_still_puts_the_stock_back(admin):
    item, sale = pending_sale(admin, qty=2)
    approve(admin, sale["id"])
    assert stock_of(admin, item) == 3
    response = void(admin, sale["id"], "Customer returned it")
    assert response.get_json()["sale"]["status"] == "voided" and stock_of(admin, item) == 5


def test_replacing_a_pending_sale_puts_back_no_stock(admin):
    item, old = pending_sale(admin, qty=3)
    new = sell(admin, [{"item_id": item["id"], "qty": 2}], replaces=old["id"]).get_json()["sale"]
    assert new["status"] == "approved"
    assert stock_of(admin, item) == 3  # 5 - 2: the pending sale never took its 3
    listed = {sale["id"]: sale for sale in day(admin).get_json()["sales"]}
    assert listed[old["id"]]["status"] == "rejected"


def test_approve_all_approves_the_days_pending_sales_in_one_step(admin):
    first, a = pending_sale(admin, qty=1)
    second, b = pending_sale(admin, qty=2, name="SPARK PLUG")
    third, c = pending_sale(admin, qty=1, name="BULB")
    void(admin, c["id"], "Not real")
    yesterday = (shop_today() - timedelta(days=1)).isoformat()
    other = sell(admin, [{"item_id": first["id"], "qty": 1}], sale_date=yesterday)  # approved already
    assert other.status_code == 201
    response = admin.post("/api/sales/approve-all", json={})
    assert response.status_code == 200 and response.get_json() == {"approved": 2, "date": today()}
    assert stock_of(admin, first) == 3 and stock_of(admin, second) == 3 and stock_of(admin, third) == 5
    again = admin.post("/api/sales/approve-all", json={"date": today()})
    assert again.get_json()["approved"] == 0


def test_approve_all_rules(admin):
    item, sale = pending_sale(admin)
    assert admin.post("/api/sales/approve-all", json={"date": "x"}).status_code == 400
    assert login("staff1").post("/api/sales/approve-all", json={}).status_code == 403
    yesterday = (shop_today() - timedelta(days=1)).isoformat()
    assert admin.post("/api/sales/approve-all", json={"date": yesterday}).get_json()["approved"] == 0
    assert day(admin).get_json()["sales"][0]["status"] == "pending"


def test_an_old_pending_sale_can_be_found_and_approved_on_its_own_day(admin):
    item = make_item(admin, stock=5)
    sale = sell(login("staff1"), [{"item_id": item["id"], "qty": 1}]).get_json()["sale"]
    yesterday = (shop_today() - timedelta(days=1)).isoformat()
    db_execute("UPDATE sales SET sale_date = ? WHERE id = ?", (yesterday, sale["id"]))
    assert day(admin, yesterday).get_json()["summary"]["pending"]["count"] == 1
    assert admin.post("/api/sales/approve-all", json={"date": yesterday}).get_json()["approved"] == 1
    assert stock_of(admin, item) == 4


def test_the_home_page_tells_the_admin_about_pending_sales(admin):
    assert "waiting for approval" not in admin.get("/dashboard").get_data(as_text=True)
    pending_sale(admin)
    html = admin.get("/dashboard").get_data(as_text=True)
    assert "1 sale waiting for approval" in html and f"/sales?date={today()}" in html
    assert "waiting for approval" not in login("staff1").get("/dashboard").get_data(as_text=True)


def test_sales_page_has_the_approve_all_button_for_the_admin_only(admin):
    assert 'id="approve-all"' in admin.get("/sales").get_data(as_text=True)
    assert 'id="approve-all"' not in login("staff1").get("/sales").get_data(as_text=True)


def test_sales_made_before_approval_existed_are_upgraded_as_approved(tmp_path):
    import sqlite3
    from mymotoworks import create_app

    path = str(tmp_path / "older.db")
    old = sqlite3.connect(path)
    # A real older database always has its users, and the sales point at them.
    old.execute("CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, "
                "username TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL, "
                "role TEXT NOT NULL CHECK (role IN ('admin', 'staff')), "
                "must_change_password INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1, "
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    old.execute("INSERT INTO users (name, username, password_hash, role) VALUES ('Administrator', 'admin', 'x', 'admin')")
    old.execute("CREATE TABLE sales (id INTEGER PRIMARY KEY AUTOINCREMENT, sale_date TEXT NOT NULL, "
                "user_id INTEGER NOT NULL, total INTEGER NOT NULL, client_ref TEXT UNIQUE, voided_at TEXT, "
                "voided_by INTEGER, void_reason TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '', "
                "replaces_sale_id INTEGER, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    old.execute("INSERT INTO sales (sale_date, user_id, total) VALUES ('2026-10-16', 1, 500)")
    old.commit()
    old.close()
    for _ in range(2):  # starting twice must not approve anything new or fail
        create_app({"DATABASE": path})
    upgraded = sqlite3.connect(path)
    row = upgraded.execute("SELECT approved_at IS NOT NULL, approved_by FROM sales").fetchall()
    assert row == [(1, 1)]  # the sales that already took stock count as approved
    upgraded.close()
