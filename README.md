# mymotoworks

Inventory, restock, sales and cash for Jaryl's Motoworks, a motor shop.

Built with Python (Flask), SQLite, vanilla JavaScript and Bootstrap 5.

## Getting started

Requires Python 3.10+.

    ./run.sh          # http://127.0.0.1:5000
    ./run.sh lan      # also reachable from other devices on the same Wi-Fi

## Tests

    .venv/bin/pytest

The plan and roadmap are in `docs/mymotoworks/plan.md` (in the ProjectWorkspace docs).

## Code structure

```
app.py                  entry point (flask --app app ...): app = create_app()
run.sh                  sets up the virtual environment and starts the app
mymotoworks/
  __init__.py           create_app(): config, database, error handlers, blueprints
  config.py             database path, secret key, cookie settings
  errors.py             ValidationError / NotFoundError / ... -> JSON {"error": ...}
  database.py           connection per request, init-db, default admin
  schema.sql            the tables
  domain/               rules with no Flask or SQL (accounts, items, money, text helpers)
  repositories/         all SQL, one class per kind of data; they never commit
  services/             use cases (auth, accounts, items, item import, sales, restocks, stock, reports); they check roles and commit
  seed.py               flask --app app seed: about 140 sample items (only when there are none)
  imports.py            reading the old spreadsheet, and the import-items command
  migrations.py         adds columns that older databases lack (runs on every start)
  exports.py            the Excel files of the reports
  web/                  Flask blueprints (pages + JSON API)
  templates/, static/   base.html, home.html, glass.css, theme.js
tests/                  pytest suite
```

Each layer only uses the ones below it: web → services → repositories / domain.
A route reads the request, calls a service, and returns JSON; a service raises
`ValidationError("...")` (or `NotFoundError`, ...) and the error becomes `{"error": "..."}`
with the right status, with nothing saved. 

## Selling

- **Sell** (staff land here after login): the whole item list is already on the page, as a flat list
  in a box of its own that scrolls (only the box scrolls, so the filter, the tabs and the page stay
  where they are). Every row has − and + to take one off or add one. Typing in the filter box
  narrows the list at once (words in any order) and says "3 of 241 items". Then change a quantity or a
  price in the cart, add a note, and save. A sale may take stock below 0 (the cart warns); wrong counts
  are fixed with stock adjustments later. On a phone the page has two tabs, Items and Cart; from 768px
  wide both show side by side.
- **Approval**: every sale, the admin's too, is **pending** when it is saved. It does not touch the
  stock and is not in the day's total or tubo (the Sales page shows it apart). The admin approves it
  (one by one, or "Approve all" for the day) and only then the stock goes down and the sale counts.
  Rejecting a pending sale takes no stock back, because none was taken. A sale that replaces another
  is pending too: the old one is voided at once, the new one counts after it is approved.
  The admin's Home page says how many sales wait for approval.
- Each sale can have an optional **note** (up to 100 characters, for example the customer's name). It
  is saved with the sale and shown under the sale number on the Sales page.
- Each cart has its own reference, so a double tap or a retry saves the sale only once. A bad line
  saves nothing and changes no stock.
- Staff record only today's sales; the admin can also pick a past day, never a future one.
- **Sales**: the day's sales, newest first, each opening to show its items, with the day's count and
  total. Staff see today only and no cost or profit. The admin picks any day and sees tubo.
- The admin can **void** an approved sale with a reason: its stock comes back (exactly what it took)
  and it leaves the totals, but it stays in the list crossed out. Sales are never deleted.

## Restocking (admin)

- **Restock** (a button on the Items page): pick the items that arrived with − and +, set the quantity
  and the **cost of one piece** (it starts at the item's current cost), add a note (like the
  supplier) and the date, and save. The stock of each item goes up and its cost (puhunan) becomes the
  cost you typed. Sales saved before keep the cost they were sold with. Only items that count stock
  can be restocked, and each item is listed once. A double tap saves one restock.
- **History**: every restock, newest first, each opening to show its items and the cost change.
- **Void** a restock with a reason: the quantities come out of the stock again, and each item's old
  cost is put back unless the cost was changed since (another restock, or an edit). The record stays,
  crossed out. Restocks are never deleted.
- Cash tracking is postponed, so a restock makes no cash-out.

## Stock corrections (admin)

All under the **Stock** menu on the Items page.

- **Adjust stock** (an item's ⋮ menu): take out or add a number of pieces, with a reason (lost,
  missing, damaged, count correction, other; "other" needs a note). The form shows "Stock 5 → 3"
  before you save.
- **Count stock**: the list of items that count stock, each with a "Counted" box. Type what is on the
  shelf; saving sets the stock of each counted item to that number. Items left empty are not touched,
  and an item whose count equals its stock makes no record. The change is worked out at the moment of
  saving, so a sale approved while you count does not spoil it.
- **Stock changes**: every adjustment and recount, newest first, with the stock before and after, the
  reason, the note, who and when. An item's ⋮ menu opens it filtered to that item.
- Nothing is edited or deleted. A mistake is fixed with another adjustment the other way round. A
  double tap on Save changes the stock once.

## Reports (admin)

The **Reports** tab, two parts:

- **Sales**: pick a month with ‹ ›. Four cards (sales, tubo, cost of what sold, spent on restocks), a
  line per day with sales, the 10 best sellers, and each month of the year. Only sales that are
  approved and not voided count, on the sale's own date. Cost and tubo use the puhunan each sale was
  made with, so a later restock never rewrites past tubo.
- **Stock**: capital in stock (puhunan × stock), what it would bring if all sold (benta × stock), tubo if
  all sold, items and pieces, low stock, out of stock, items below zero and the 10 items where the most
  money sits. Only active items that count stock; a stock below 0 counts as 0 in the values.
- **Download Excel** on each part: `mymotoworks-sales-2026-10.xlsx` (Days, Best sellers, Months) and
  `mymotoworks-stock.xlsx` (Summary, Low stock, All items). Money cells are numbers, and a name that
  starts with `=`, `+`, `-` or `@` stays text.

## Loading the old spreadsheet

One time, into a new database with no items:

    .venv/bin/flask --app app import-items "path/to/JARYLS MOTOWORKS.xlsx" --dry-run     # preview only
    .venv/bin/flask --app app import-items "path/to/JARYLS MOTOWORKS.xlsx" -v --dry-run  # list every item
    .venv/bin/flask --app app import-items "path/to/JARYLS MOTOWORKS.xlsx"               # asks, then imports

It reads the `STOCK INVENTORY` sheet: item name, model, part no., puhunan, benta and the
`REMAINING STOCK` column (the sheet's count after sales). Re-order is set to 0 for every item
(the sheet's RE-ORDER column is restocked quantity, so it is not used). Rows with a problem
(no price, no name) are skipped and listed with their row number: add those by hand on the Items
page. A missing puhunan counts as 0. If the shop already has items the import is refused.
Past sales are not imported, and October sales are not in the sheet, so recount the shelves
after loading.

## Roles

- **admin**: the owner. Everything, including the Users page. The default account is `admin` / `admin`,
  created on the first start; its password must be changed at the first login.
- **staff**: records sales and cash-outs and views items. Never sees cost (puhunan) or profit (tubo):
  the server leaves those fields out of every answer for staff.

Only the admin adds, edits and deactivates items. Money is stored as whole centavos.

There is no sign-up: the admin creates all accounts and gives each person a temporary password,
shown once. Five wrong passwords lock that username on that device for five minutes.
