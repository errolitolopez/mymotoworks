"""The one-time import of items from the old spreadsheet."""

from conftest import login, make_item, make_workbook

GOOD = [
    ("AIR FILTER SUNTAL", "MIOi125 M3", "YA040A", 103.5, 150, 3),
    ("ARMAK TAPE 5 YARDS", None, None, 21, 30, 9),
]


def run(app, path, *options):
    return app.test_cli_runner().invoke(args=["import-items", path, *options])


def test_dry_run_shows_the_plan_and_saves_nothing(app, tmp_path, admin):
    result = run(app, make_workbook(tmp_path / "shop.xlsx", GOOD), "--dry-run")
    assert result.exit_code == 0, result.output
    assert "Will import 2 items" in result.output
    assert admin.get("/api/items").get_json()["total"] == 0


def test_prices_become_exact_centavos_rounded_half_up(app, tmp_path):
    rows = [
        ("A", None, None, 133.19999999999999, 270, 1),
        ("B", None, None, 20.83, 30, 1),
        ("C", None, None, 2.675, 5, 1),
        ("D", None, None, 0.005, 1, 1),
        ("E", None, None, "1,250.50", "₱300", 1),
    ]
    result = run(app, make_workbook(tmp_path / "shop.xlsx", rows), "--dry-run", "-v")
    assert result.exit_code == 0, result.output
    # The preview lists each cleaned item so the owner can check the money.
    for line in ("puhunan 133.20 | benta 270.00", "puhunan 20.83 | benta 30.00", "puhunan 2.68 | benta 5.00",
                 "puhunan 0.01 | benta 1.00", "puhunan 1,250.50 | benta 300.00"):
        assert line in result.output, line


def test_part_number_typed_as_a_number_stays_whole(app, tmp_path):
    rows = [("BAJAJ GENUINE VALVE SEAL", "CT100", 39103519, 81, 250, 10),
            ("OTHER", None, 12.0, 1, 2, 1)]
    result = run(app, make_workbook(tmp_path / "shop.xlsx", rows), "--dry-run", "-v")
    assert "39103519" in result.output and "39103519.0" not in result.output
    assert "12.0" not in result.output


def test_problem_rows_are_listed_with_their_row_numbers(app, tmp_path):
    rows = [
        ("GOOD ONE", None, None, 10, 20, 1),
        (" ", "CLICK125", None, 10, 20, 1),            # row 4: no item name
        ("NO PRICE", None, None, 10, None, 1),          # row 5
        ("TEXT PRICE", None, None, 10, "abc", 1),       # row 6
        ("NEGATIVE", None, None, 10, -5, 1),            # row 7
        ("FRACTION STOCK", None, None, 10, 20, 1.5),    # row 8
        ("TEXT STOCK", None, None, 10, 20, "many"),     # row 9
        ("X" * 121, None, None, 10, 20, 1),             # row 10
        ("243", None, None, None, None, None),          # row 11: junk
        (None, None, None, None, None, None),           # row 12: empty, not a problem
        ("   ", None, None, None, None, None),          # row 13: only spaces, not a problem
    ]
    result = run(app, make_workbook(tmp_path / "shop.xlsx", rows), "--dry-run")
    assert result.exit_code == 0, result.output
    assert "Will import 1 item" in result.output
    assert "Skipped 8 rows" in result.output
    for number in range(4, 12):
        assert f"Row {number}:" in result.output
    assert "Row 12:" not in result.output and "Row 13:" not in result.output
    assert "Item name is required." in result.output
    assert "Benta (price) is missing." in result.output


def test_missing_puhunan_counts_as_zero_and_blank_stock_as_zero(app, tmp_path):
    rows = [("LINIS PART", None, None, None, 50, None), ("OK", None, None, 5, 10, 2)]
    result = run(app, make_workbook(tmp_path / "shop.xlsx", rows), "--dry-run")
    assert "Will import 2 items" in result.output
    assert "1 item has no puhunan (counted as 0)" in result.output


def test_lookalike_rows_are_warned_about_but_not_skipped(app, tmp_path):
    rows = [("BEARING 6301 2RS SILL", None, None, 10, 20, 5),
            ("bearing  6301 2rs sill", None, None, 10, 20, 4)]
    result = run(app, make_workbook(tmp_path / "shop.xlsx", rows), "--dry-run")
    assert "Will import 2 items" in result.output
    assert "Row 4 looks the same as row 3" in result.output


def test_the_reorder_column_is_ignored(app, tmp_path):
    result = run(app, make_workbook(tmp_path / "shop.xlsx", GOOD), "--dry-run", "-v")
    assert "re-order 0" in result.output


def test_file_problems_give_one_clear_message_and_import_nothing(app, tmp_path, admin):
    missing = run(app, str(tmp_path / "nope.xlsx"), "--dry-run")
    assert missing.exit_code != 0 and "Cannot find the file" in missing.output

    text_file = tmp_path / "fake.xlsx"
    text_file.write_text("this is not excel")
    fake = run(app, str(text_file), "--dry-run")
    assert fake.exit_code != 0 and "Cannot read that file" in fake.output

    wrong_sheet = run(app, make_workbook(tmp_path / "a.xlsx", GOOD, sheet="PRICES"), "--dry-run")
    assert wrong_sheet.exit_code != 0 and 'no sheet named "STOCK INVENTORY"' in wrong_sheet.output

    no_column = run(app, make_workbook(tmp_path / "b.xlsx", GOOD, headings=["ITEM NAME", "MODEL"]), "--dry-run")
    assert no_column.exit_code != 0 and 'no "PART NO." column' in no_column.output

    no_header = run(app, make_workbook(tmp_path / "c.xlsx", GOOD, headings=["x", "y"]), "--dry-run")
    assert no_header.exit_code != 0 and '"ITEM NAME"' in no_header.output

    assert admin.get("/api/items").get_json()["total"] == 0


def test_headings_may_have_extra_spaces_and_other_capitals(app, tmp_path):
    headings = [" Item Name", "model ", "Part No.", "puhunan", "BENTA", "stock", "x", "re-order", "Remaining Stock"]
    result = run(app, make_workbook(tmp_path / "shop.xlsx", GOOD, headings=headings), "--dry-run")
    assert result.exit_code == 0 and "Will import 2 items" in result.output


def test_dry_run_on_a_shop_with_items_says_the_real_import_would_be_refused(app, tmp_path, admin):
    make_item(admin)
    result = run(app, make_workbook(tmp_path / "shop.xlsx", GOOD), "--dry-run")
    assert result.exit_code == 0
    assert "already has 1 item" in result.output and "would be refused" in result.output


def items_of(admin):
    return admin.get("/api/items?per_page=100").get_json()["items"]


def test_import_adds_the_good_rows_exactly(app, tmp_path, admin):
    rows = GOOD + [("BAJAJ GENUINE VALVE SEAL", "CT100", 39103519, 81, 250, 10),
                   ("NO PRICE", None, None, 5, None, 1)]
    result = run(app, make_workbook(tmp_path / "shop.xlsx", rows), "--yes")
    assert result.exit_code == 0, result.output
    assert "Imported 3 items." in result.output
    by_name = {item["name"]: item for item in items_of(admin)}
    assert set(by_name) == {"AIR FILTER SUNTAL", "ARMAK TAPE 5 YARDS", "BAJAJ GENUINE VALVE SEAL"}
    air = by_name["AIR FILTER SUNTAL"]
    assert air["puhunan"] == 10350 and air["benta"] == 15000 and air["stock"] == 3
    assert air["model"] == "MIOi125 M3" and air["part_no"] == "YA040A"
    assert air["reorder_level"] == 0 and air["track_stock"] is True and air["active"] is True
    tape = by_name["ARMAK TAPE 5 YARDS"]
    assert tape["model"] == "" and tape["part_no"] == "" and tape["stock"] == 9
    assert by_name["BAJAJ GENUINE VALVE SEAL"]["part_no"] == "39103519"


def test_the_reorder_column_does_not_become_stock_or_reorder(app, tmp_path, admin):
    run(app, make_workbook(tmp_path / "shop.xlsx", GOOD), "--yes")
    for item in items_of(admin):
        assert item["reorder_level"] == 0 and item["stock"] in (3, 9)  # not 7 (RE-ORDER) or 99 (STOCK)


def test_staff_see_imported_items_without_cost(app, tmp_path):
    run(app, make_workbook(tmp_path / "shop.xlsx", GOOD), "--yes")
    text = login("staff1").get("/api/items").get_data(as_text=True)
    assert "AIR FILTER SUNTAL" in text and "puhunan" not in text


def test_the_confirmation_question_can_stop_the_import(app, tmp_path, admin):
    path = make_workbook(tmp_path / "shop.xlsx", GOOD)
    no = app.test_cli_runner().invoke(args=["import-items", path], input="n\n")
    assert "Import 2 items?" in no.output and "Nothing imported." in no.output
    assert admin.get("/api/items").get_json()["total"] == 0
    yes = app.test_cli_runner().invoke(args=["import-items", path], input="y\n")
    assert "Imported 2 items." in yes.output
    assert admin.get("/api/items").get_json()["total"] == 2


def test_a_second_import_is_refused_and_changes_nothing(app, tmp_path, admin):
    path = make_workbook(tmp_path / "shop.xlsx", GOOD)
    assert run(app, path, "--yes").exit_code == 0
    again = run(app, path, "--yes")
    assert again.exit_code != 0 and "already has" in again.output
    assert admin.get("/api/items").get_json()["total"] == 2


def test_deactivated_items_also_block_the_import(app, tmp_path, admin):
    item = make_item(admin)
    admin.put(f"/api/items/{item['id']}", json={"active": False})
    result = run(app, make_workbook(tmp_path / "shop.xlsx", GOOD), "--yes")
    assert result.exit_code != 0 and "already has" in result.output
    assert admin.get("/api/items?inactive=1").get_json()["total"] == 1


def test_nothing_to_import_is_a_plain_message(app, tmp_path, admin):
    result = run(app, make_workbook(tmp_path / "shop.xlsx", [("NO PRICE", None, None, 5, None, 1)]), "--yes")
    assert result.exit_code != 0 and "nothing to import" in result.output.lower()


def test_a_failure_while_saving_leaves_the_database_unchanged(app, tmp_path, admin, monkeypatch):
    from mymotoworks.repositories.items import ItemRepository
    real_create = ItemRepository.create
    calls = []

    def fail_on_second(self, fields):
        calls.append(fields["name"])
        if len(calls) == 2:
            raise RuntimeError("disk full")
        return real_create(self, fields)

    monkeypatch.setattr(ItemRepository, "create", fail_on_second)
    result = run(app, make_workbook(tmp_path / "shop.xlsx", GOOD), "--yes")
    assert result.exit_code != 0
    assert admin.get("/api/items").get_json()["total"] == 0
