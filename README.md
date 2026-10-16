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
  services/             use cases (auth, accounts, items, item import, sales); they check roles and commit
  seed.py               flask --app app seed: about 140 sample items (only when there are none)
  imports.py            reading the old spreadsheet, and the import-items command
  migrations.py         adds columns that older databases lack (runs on every start)
  web/                  Flask blueprints (pages + JSON API)
  templates/, static/   base.html, home.html, glass.css, theme.js
tests/                  pytest suite
```

Each layer only uses the ones below it: web → services → repositories / domain.
A route reads the request, calls a service, and returns JSON; a service raises
`ValidationError("...")` (or `NotFoundError`, ...) and the error becomes `{"error": "..."}`
with the right status, with nothing saved. 

## Selling

- **Sell** (staff land here after login): the whole item list is already on the page, grouped by the
  first word of the name ("BRAKE (29)", closed at first, so the page stays short; an item that is
  alone in its group shows as its own row). Every row has − and + to take one off or add one.
  Typing in the filter box narrows the list at once (words in any order) and opens the groups that
  match. Then change a quantity or a price in the cart, add a note, and save. A sale may take stock
  below 0 (the cart warns); wrong counts are fixed with stock adjustments later. On a phone the
  page has two tabs, Items and Cart; from 768px wide both show side by side.
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
