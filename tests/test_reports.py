"""Reports: the sales report (feature A), the stock report (B) and the Excel downloads (C)."""

from datetime import timedelta

from conftest import db_execute, login, make_item

from mymotoworks.config import shop_today


def this_month():
    return shop_today().strftime("%Y-%m")


def make_sale(admin, item, qty=2, benta=None, date=None, approve=True):
    """A sale of the item. By default it is approved at once, the way the admin does at the end of a day."""
    line = {"item_id": item["id"], "qty": qty}
    if benta is not None:
        line["benta"] = benta
    body = {"lines": [line]}
    if date:
        body["sale_date"] = date
    response = admin.post("/api/sales", json=body)
    assert response.status_code == 201, response.get_json()
    sale = response.get_json()["sale"]
    if approve:
        assert admin.post(f"/api/sales/{sale['id']}/approve").status_code == 200
    return sale


def report(client, month=None):
    return client.get("/api/reports/sales" + (f"?month={month}" if month else ""))


def test_an_empty_month(admin):
    data = report(admin).get_json()
    assert data == {"month": this_month(), "days": [], "restocked": 0, "best_sellers": [],
                    "totals": {"sales": 0, "pieces": 0, "total": 0, "cost": 0, "tubo": 0}}


def test_one_sale_gives_total_cost_and_tubo(admin):
    item = make_item(admin, stock=9)  # benta 15000, puhunan 10350
    make_sale(admin, item, qty=2)
    data = report(admin).get_json()
    day = data["days"][0]
    assert day["date"] == shop_today().isoformat()
    assert (day["sales"], day["pieces"], day["total"], day["cost"], day["tubo"]) == (1, 2, 30000, 20700, 9300)
    assert data["totals"] == {"sales": 1, "pieces": 2, "total": 30000, "cost": 20700, "tubo": 9300}


def test_a_changed_price_changes_total_and_tubo(admin):
    item = make_item(admin, stock=9)
    make_sale(admin, item, qty=2, benta=14000)
    totals = report(admin).get_json()["totals"]
    assert totals["total"] == 28000 and totals["tubo"] == 28000 - 20700


def test_pending_voided_and_rejected_sales_are_left_out(admin):
    item = make_item(admin, stock=50)
    make_sale(admin, item, qty=1)                                   # counts
    make_sale(admin, item, qty=1, approve=False)                    # pending
    voided = make_sale(admin, item, qty=1)
    admin.post(f"/api/sales/{voided['id']}/void", json={"reason": "Mistake"})
    rejected = make_sale(admin, item, qty=1, approve=False)
    admin.post(f"/api/sales/{rejected['id']}/void", json={"reason": "No"})
    data = report(admin).get_json()
    assert data["totals"]["sales"] == 1 and data["totals"]["total"] == 15000


def test_several_sales_add_up_per_day_and_days_are_in_order(admin):
    item = make_item(admin, stock=50)
    today = shop_today()
    earlier = (today.replace(day=1)).isoformat()
    make_sale(admin, item, qty=1)
    make_sale(admin, item, qty=3)
    make_sale(admin, item, qty=1, date=earlier)
    days = report(admin).get_json()["days"]
    if earlier == today.isoformat():          # the 1st of the month: everything is on one day
        assert len(days) == 1 and days[0]["sales"] == 3
    else:
        assert [day["date"] for day in days] == [earlier, today.isoformat()]
        assert days[0]["sales"] == 1 and days[1]["sales"] == 2 and days[1]["pieces"] == 4


def test_sales_of_other_months_are_left_out(admin):
    item = make_item(admin, stock=50)
    today = shop_today()
    first_of_month = today.replace(day=1)
    last_month_day = (first_of_month - timedelta(days=1)).isoformat()
    make_sale(admin, item, qty=1, date=last_month_day)
    make_sale(admin, item, qty=1)
    assert report(admin).get_json()["totals"]["sales"] == 1
    previous = last_month_day[:7]
    assert report(admin, previous).get_json()["totals"]["sales"] == 1
    assert report(admin, "2020-01").get_json()["days"] == []


def test_old_sales_keep_the_cost_they_were_sold_with(admin):
    item = make_item(admin, stock=9)  # puhunan 10350
    make_sale(admin, item, qty=1)
    admin.post("/api/restocks", json={"lines": [{"item_id": item["id"], "qty": 5, "puhunan": 12000}]})
    make_sale(admin, item, qty=1)
    totals = report(admin).get_json()["totals"]
    assert totals["cost"] == 10350 + 12000 and totals["tubo"] == (15000 - 10350) + (15000 - 12000)


def test_restock_spending_counts_the_months_restocks_that_are_not_voided(admin):
    item = make_item(admin, stock=1)
    admin.post("/api/restocks", json={"lines": [{"item_id": item["id"], "qty": 2, "puhunan": 10000}]})   # 20000
    voided = admin.post("/api/restocks", json={"lines": [{"item_id": item["id"], "qty": 5, "puhunan": 10000}]}).get_json()["restock"]
    admin.post(f"/api/restocks/{voided['id']}/void", json={"reason": "Mistake"})
    last_month = (shop_today().replace(day=1) - timedelta(days=1)).isoformat()
    admin.post("/api/restocks", json={"lines": [{"item_id": item["id"], "qty": 1, "puhunan": 10000}], "restock_date": last_month})
    assert report(admin).get_json()["restocked"] == 20000
    assert report(admin, last_month[:7]).get_json()["restocked"] == 10000


def test_best_sellers_are_ordered_by_pieces_and_limited_to_ten(admin):
    items = [make_item(admin, name=f"ITEM {n:02d}", stock=100) for n in range(1, 13)]
    for number, item in enumerate(items, start=1):
        make_sale(admin, item, qty=number)           # ITEM 12 sold the most
    best = report(admin).get_json()["best_sellers"]
    assert len(best) == 10
    assert [row["name"] for row in best][:3] == ["ITEM 12", "ITEM 11", "ITEM 10"]
    assert best[0]["pieces"] == 12 and best[0]["total"] == 12 * 15000 and best[0]["tubo"] == 12 * (15000 - 10350)


def test_best_sellers_leave_out_sales_that_do_not_count(admin):
    item = make_item(admin, stock=50)
    make_sale(admin, item, qty=5, approve=False)
    assert report(admin).get_json()["best_sellers"] == []


def test_bad_months_are_refused(admin):
    for bad in ("2026-13", "26-10", "2026-1", "202610", "abc", "2026-00", "1999-12", "2101-01", "2026-10-01"):
        response = admin.get(f"/api/reports/sales?month={bad}")
        assert response.status_code == 400, bad
        assert response.get_json()["error"] == "Month must look like 2026-10.", bad
    assert admin.get("/api/reports/sales?month=").status_code == 200      # empty means this month
    assert admin.get("/api/reports/sales?month=a&month=b").status_code == 400


def test_the_year_by_month(admin):
    item = make_item(admin, stock=50)
    make_sale(admin, item, qty=2)
    data = admin.get(f"/api/reports/months?year={shop_today().year}").get_json()
    assert data["year"] == shop_today().year
    assert data["months"] == [{"month": this_month(), "sales": 1, "pieces": 2, "total": 30000, "cost": 20700, "tubo": 9300}]
    assert admin.get("/api/reports/months?year=2020").get_json() == {"year": 2020, "months": []}
    for bad in ("abc", "99", "1999", "2101", "2026-10"):
        response = admin.get(f"/api/reports/months?year={bad}")
        assert response.status_code == 400 and response.get_json()["error"] == "Year must look like 2026.", bad
    assert admin.get("/api/reports/months").status_code == 200


def test_reports_are_for_the_admin_only(admin, client):
    assert report(login("staff1")).status_code == 403
    assert admin.get("/reports").status_code == 200
    assert login("staff1").get("/reports").status_code == 302
    assert report(client).status_code == 401
    assert client.get("/reports").status_code == 302


def test_the_reports_page_has_its_parts(admin):
    html = admin.get("/reports").get_data(as_text=True)
    for element in ('id="tab-sales"', 'id="tab-stock"', 'id="month-label"', 'id="prev-month"', 'id="next-month"',
                    'id="day-list"', 'id="best-list"', 'id="year-list"'):
        assert element in html, element
