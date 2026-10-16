"""Stock adjustments (feature A), their history (B) and the recount (C)."""

from conftest import db_query, login, make_item


def adjust(client, lines, reason="lost", **extra):
    return client.post("/api/stock-adjustments", json={"reason": reason, "lines": lines, **extra})


def item_row(admin, item):
    rows = admin.get("/api/items/all").get_json()["items"]
    return next(row for row in rows if row["id"] == item["id"])


def count_rows(table):
    return db_query(f"SELECT COUNT(*) AS n FROM {table}")[0]["n"]


def test_taking_out_lowers_the_stock_and_records_before_and_after(admin):
    item = make_item(admin, stock=5)
    response = adjust(admin, [{"item_id": item["id"], "change": -2}], note="  Dropped   in the shop ")
    assert response.status_code == 201, response.get_json()
    batch = response.get_json()["batch"]
    assert batch["kind"] == "adjustment" and batch["reason"] == "lost" and batch["reason_label"] == "Lost"
    assert batch["note"] == "Dropped in the shop" and batch["recorded_by"] == "Administrator"
    line = batch["adjustments"][0]
    assert line["change"] == -2 and line["stock_before"] == 5 and line["stock_after"] == 3
    assert line["name"] == "AIR FILTER SUNTAL"
    assert item_row(admin, item)["stock"] == 3


def test_adding_raises_the_stock(admin):
    item = make_item(admin, stock=1)
    assert adjust(admin, [{"item_id": item["id"], "change": 4}], reason="count_correction").status_code == 201
    assert item_row(admin, item)["stock"] == 5


def test_the_stock_may_go_below_zero(admin):
    item = make_item(admin, stock=1)
    assert adjust(admin, [{"item_id": item["id"], "change": -3}]).status_code == 201
    assert item_row(admin, item)["stock"] == -2


def test_several_items_in_one_save(admin):
    first, second = make_item(admin, stock=5), make_item(admin, name="SPARK PLUG", stock=2)
    batch = adjust(admin, [{"item_id": first["id"], "change": -1}, {"item_id": second["id"], "change": 3}],
                   reason="damaged").get_json()["batch"]
    assert len(batch["adjustments"]) == 2 and batch["reason_label"] == "Damaged"
    assert item_row(admin, first)["stock"] == 4 and item_row(admin, second)["stock"] == 5


def test_other_needs_a_note_and_every_reason_works(admin):
    item = make_item(admin, stock=50)
    line = [{"item_id": item["id"], "change": -1}]
    refused = adjust(admin, line, reason="other")
    assert refused.status_code == 400 and refused.get_json()["error"] == "Write a note when the reason is Other."
    assert adjust(admin, line, reason="other", note="Given to a neighbour").status_code == 201
    for reason in ("lost", "missing", "damaged", "count_correction"):
        assert adjust(admin, line, reason=reason).status_code == 201, reason
    assert item_row(admin, item)["stock"] == 50 - 5


def test_a_bad_line_saves_nothing_and_changes_no_stock(admin):
    good = make_item(admin, stock=5)
    loose = make_item(admin, name="LINIS", track_stock=False)
    for bad, message in (({"item_id": 9999, "change": 1}, "An item in the list does not exist."),
                         ({"item_id": loose["id"], "change": 1}, "LINIS does not count stock.")):
        response = adjust(admin, [{"item_id": good["id"], "change": -2}, bad])
        assert response.status_code == 400 and response.get_json()["error"] == message
    assert item_row(admin, good)["stock"] == 5
    assert count_rows("stock_batches") == 0 and count_rows("stock_adjustments") == 0


def test_the_same_item_twice_is_refused(admin):
    item = make_item(admin, stock=5)
    line = {"item_id": item["id"], "change": -1}
    response = adjust(admin, [line, line])
    assert response.status_code == 400 and response.get_json()["error"] == "An item is listed twice."
    assert item_row(admin, item)["stock"] == 5


def test_adjustment_rules(admin):
    item = make_item(admin, stock=5)
    ok = {"item_id": item["id"], "change": -1}
    change = "Change must be a whole number, not 0, from -1000000 to 1000000."
    cases = [
        ({"lines": []}, "Add at least one item."),
        ({"lines": "x"}, "Add at least one item."),
        ({"lines": ["x"]}, "Add at least one item."),
        ({"lines": [{"item_id": n, "change": 1} for n in range(1, 102)]}, "A save can have at most 100 items."),
        ({"lines": [{**ok, "change": 0}]}, change),
        ({"lines": [{**ok, "change": 1.5}]}, change),
        ({"lines": [{**ok, "change": "2"}]}, change),
        ({"lines": [{**ok, "change": True}]}, change),
        ({"lines": [{**ok, "change": 1_000_001}]}, change),
        ({"lines": [{**ok, "change": -1_000_001}]}, change),
        ({"lines": [{"change": 1}]}, "An item in the list does not exist."),
        ({"lines": [{**ok, "item_id": "1"}]}, "An item in the list does not exist."),
        ({"lines": [{**ok, "item_id": True}]}, "An item in the list does not exist."),
        ({"lines": [ok], "reason": "stolen"}, "Choose a reason."),
        ({"lines": [ok], "reason": None}, "Choose a reason."),
        ({"lines": [ok], "note": "x" * 201}, "Note can be at most 200 characters."),
        ({"lines": [ok], "note": 5}, "Note must be text."),
        ({"lines": [ok], "client_ref": 5}, "That reference is not valid."),
        ({"lines": [ok], "client_ref": "x" * 65}, "That reference is not valid."),
    ]
    for body, message in cases:
        response = admin.post("/api/stock-adjustments", json={"reason": "lost", **body})
        assert response.status_code == 400 and response.get_json()["error"] == message, body
    assert item_row(admin, item)["stock"] == 5 and count_rows("stock_batches") == 0


def test_no_body_is_refused(admin):
    assert admin.post("/api/stock-adjustments").status_code == 400


def test_a_double_tap_with_the_same_reference_changes_the_stock_once(admin):
    item = make_item(admin, stock=5)
    line = [{"item_id": item["id"], "change": -2}]
    first = adjust(admin, line, client_ref="a-1")
    second = adjust(admin, line, client_ref="a-1")
    assert first.status_code == 201 and second.status_code == 200 and second.get_json()["duplicate"] is True
    assert second.get_json()["batch"]["id"] == first.get_json()["batch"]["id"]
    assert item_row(admin, item)["stock"] == 3 and count_rows("stock_adjustments") == 1


def test_staff_and_visitors_cannot_adjust(admin, client):
    item = make_item(admin, stock=5)
    line = [{"item_id": item["id"], "change": -1}]
    assert adjust(login("staff1"), line).status_code == 403
    assert adjust(client, line).status_code == 401
    assert item_row(admin, item)["stock"] == 5


def history(client, query=""):
    return client.get("/api/stock-adjustments" + query)


def many_adjustments(admin, count, item=None):
    item = item or make_item(admin, stock=1000)
    for _ in range(count):
        assert adjust(admin, [{"item_id": item["id"], "change": -1}]).status_code == 201
    return item


def test_the_history_lists_changes_newest_first_with_all_the_details(admin):
    item = make_item(admin, stock=10)
    adjust(admin, [{"item_id": item["id"], "change": -2}], reason="lost", note="Dropped")
    adjust(admin, [{"item_id": item["id"], "change": 5}], reason="count_correction")
    data = history(admin).get_json()
    assert data["total"] == 2 and data["page"] == 1 and data["pages"] == 1 and data["item"] is None
    newest, oldest = data["adjustments"]
    assert newest["change"] == 5 and newest["stock_before"] == 8 and newest["stock_after"] == 13
    assert newest["reason"] == "count_correction" and newest["reason_label"] == "Count correction"
    assert oldest["change"] == -2 and oldest["stock_before"] == 10 and oldest["stock_after"] == 8
    assert oldest["note"] == "Dropped" and oldest["recorded_by"] == "Administrator" and oldest["kind"] == "adjustment"
    assert oldest["name"] == "AIR FILTER SUNTAL" and oldest["item_id"] == item["id"]


def test_the_history_can_be_filtered_by_item(admin):
    first, second = make_item(admin, stock=10), make_item(admin, name="SPARK PLUG", stock=10)
    adjust(admin, [{"item_id": first["id"], "change": -1}])
    adjust(admin, [{"item_id": second["id"], "change": -2}])
    data = history(admin, f"?item={second['id']}").get_json()
    assert [row["item_id"] for row in data["adjustments"]] == [second["id"]]
    assert data["item"] == {"id": second["id"], "name": "SPARK PLUG", "stock": 8}
    assert history(admin, "?item=9999").status_code == 404
    assert history(admin, "?item=abc").get_json()["total"] == 2  # a bad number means no filter


def test_the_history_is_paged(admin):
    many_adjustments(admin, 25)
    first = history(admin).get_json()
    assert first["total"] == 25 and first["pages"] == 2 and len(first["adjustments"]) == 20
    assert len(history(admin, "?page=2").get_json()["adjustments"]) == 5
    assert history(admin, "?page=99").get_json()["adjustments"] == []
    assert history(admin, "?page=0").get_json()["page"] == 1
    assert history(admin, "?page=abc").get_json()["page"] == 1
    assert len(history(admin, "?per_page=5").get_json()["adjustments"]) == 5
    assert len(history(admin, "?per_page=5000").get_json()["adjustments"]) == 25  # capped at 50


def test_an_empty_history(admin):
    assert history(admin).get_json() == {"adjustments": [], "page": 1, "pages": 1, "total": 0, "item": None}


def test_the_time_is_shown_in_shop_time(admin):
    from conftest import db_execute
    item = make_item(admin, stock=5)
    batch = adjust(admin, [{"item_id": item["id"], "change": -1}]).get_json()["batch"]
    db_execute("UPDATE stock_batches SET created_at = '2026-10-16 02:30:00' WHERE id = ?", (batch["id"],))
    assert history(admin).get_json()["adjustments"][0]["recorded_at"] == "10:30"  # UTC+8


def test_the_history_is_for_the_admin_only(admin, client):
    assert history(login("staff1")).status_code == 403
    assert history(client).status_code == 401
    assert admin.get("/stock-history").status_code == 200
    assert login("staff1").get("/stock-history").status_code == 302
    assert client.get("/stock-history").status_code == 302


def test_the_history_page_and_the_menus_link_to_it(admin):
    html = admin.get("/stock-history").get_data(as_text=True)
    assert 'id="adjustment-list"' in html and 'id="pager"' in html
    assert 'href="/stock-history"' in admin.get("/items").get_data(as_text=True)


def count(client, lines, **extra):
    return client.post("/api/stock-counts", json={"lines": lines, **extra})


def test_a_recount_sets_the_stock_to_what_was_counted(admin):
    first, second = make_item(admin, stock=10), make_item(admin, name="SPARK PLUG", stock=4)
    response = count(admin, [{"item_id": first["id"], "counted": 7}, {"item_id": second["id"], "counted": 9}],
                     note="October shelf count")
    assert response.status_code == 201, response.get_json()
    data = response.get_json()
    assert data["changed"] == 2 and data["unchanged"] == 0 and data["duplicate"] is False
    batch = data["batch"]
    assert batch["kind"] == "recount" and batch["reason"] == "count_correction" and batch["note"] == "October shelf count"
    changes = {line["item_id"]: line for line in batch["adjustments"]}
    assert changes[first["id"]]["change"] == -3 and changes[first["id"]]["stock_before"] == 10
    assert changes[second["id"]]["change"] == 5 and changes[second["id"]]["stock_after"] == 9
    assert item_row(admin, first)["stock"] == 7 and item_row(admin, second)["stock"] == 9


def test_an_item_whose_count_equals_its_stock_makes_no_record(admin):
    same, different = make_item(admin, stock=5), make_item(admin, name="SPARK PLUG", stock=5)
    data = count(admin, [{"item_id": same["id"], "counted": 5}, {"item_id": different["id"], "counted": 3}]).get_json()
    assert data["changed"] == 1 and data["unchanged"] == 1
    assert [line["item_id"] for line in data["batch"]["adjustments"]] == [different["id"]]
    assert count_rows("stock_adjustments") == 1


def test_a_recount_where_nothing_changed_makes_no_batch(admin):
    item = make_item(admin, stock=5)
    response = count(admin, [{"item_id": item["id"], "counted": 5}])
    assert response.status_code == 200
    assert response.get_json() == {"batch": None, "changed": 0, "unchanged": 1, "duplicate": False}
    assert count_rows("stock_batches") == 0


def test_a_counted_zero_and_a_negative_stock_both_work(admin):
    from conftest import db_execute
    low, negative = make_item(admin, stock=4), make_item(admin, name="SPARK PLUG", stock=0)
    db_execute("UPDATE items SET stock = -2 WHERE id = ?", (negative["id"],))  # sold more than was counted
    count(admin, [{"item_id": low["id"], "counted": 0}, {"item_id": negative["id"], "counted": 3}])
    assert item_row(admin, low)["stock"] == 0 and item_row(admin, negative)["stock"] == 3


def test_the_stock_ends_at_the_counted_number_even_if_it_changed_while_counting(admin):
    item = make_item(admin, stock=10)
    # The page showed 10. A sale is approved while the owner counts the shelf.
    sale = admin.post("/api/sales", json={"lines": [{"item_id": item["id"], "qty": 2}]}).get_json()["sale"]
    admin.post(f"/api/sales/{sale['id']}/approve")
    assert item_row(admin, item)["stock"] == 8
    data = count(admin, [{"item_id": item["id"], "counted": 9}]).get_json()
    assert item_row(admin, item)["stock"] == 9
    line = data["batch"]["adjustments"][0]
    assert line["stock_before"] == 8 and line["change"] == 1 and line["stock_after"] == 9


def test_a_double_tap_with_the_same_reference_counts_once(admin):
    item = make_item(admin, stock=10)
    line = [{"item_id": item["id"], "counted": 6}]
    first = count(admin, line, client_ref="c-1")
    second = count(admin, line, client_ref="c-1")
    assert first.status_code == 201 and second.status_code == 200 and second.get_json()["duplicate"] is True
    assert second.get_json()["batch"]["id"] == first.get_json()["batch"]["id"]
    assert item_row(admin, item)["stock"] == 6 and count_rows("stock_adjustments") == 1


def test_a_bad_line_in_a_recount_changes_nothing(admin):
    good = make_item(admin, stock=10)
    loose = make_item(admin, name="LINIS", track_stock=False)
    for bad, message in (({"item_id": 9999, "counted": 1}, "An item in the list does not exist."),
                         ({"item_id": loose["id"], "counted": 1}, "LINIS does not count stock.")):
        response = count(admin, [{"item_id": good["id"], "counted": 1}, bad])
        assert response.status_code == 400 and response.get_json()["error"] == message
    assert item_row(admin, good)["stock"] == 10 and count_rows("stock_batches") == 0


def test_recount_rules(admin):
    item = make_item(admin, stock=5)
    ok = {"item_id": item["id"], "counted": 3}
    counted = "Counted must be a whole number from 0 to 1000000."
    cases = [
        ({"lines": []}, "Add at least one item."),
        ({"lines": [{**ok, "counted": -1}]}, counted),
        ({"lines": [{**ok, "counted": 1.5}]}, counted),
        ({"lines": [{**ok, "counted": "3"}]}, counted),
        ({"lines": [{**ok, "counted": True}]}, counted),
        ({"lines": [{**ok, "counted": None}]}, counted),
        ({"lines": [{**ok, "counted": 1_000_001}]}, counted),
        ({"lines": [ok, ok]}, "An item is listed twice."),
        ({"lines": [{"counted": 1}]}, "An item in the list does not exist."),
        ({"lines": [ok], "note": "x" * 201}, "Note can be at most 200 characters."),
        ({"lines": [ok], "client_ref": 5}, "That reference is not valid."),
    ]
    for body, message in cases:
        response = admin.post("/api/stock-counts", json=body)
        assert response.status_code == 400 and response.get_json()["error"] == message, body
    assert item_row(admin, item)["stock"] == 5 and count_rows("stock_batches") == 0
    assert admin.post("/api/stock-counts").status_code == 400


def test_staff_cannot_recount_and_the_page_is_for_the_admin(admin, client):
    item = make_item(admin, stock=5)
    assert count(login("staff1"), [{"item_id": item["id"], "counted": 1}]).status_code == 403
    assert count(client, []).status_code == 401
    assert item_row(admin, item)["stock"] == 5
    html = admin.get("/stock-count").get_data(as_text=True)
    for element in ('id="item-filter"', 'id="item-list"', 'id="save-count"', 'id="count-note"', 'id="count-summary"'):
        assert element in html, element
    assert login("staff1").get("/stock-count").status_code == 302
    assert 'href="/stock-count"' in admin.get("/items").get_data(as_text=True)
