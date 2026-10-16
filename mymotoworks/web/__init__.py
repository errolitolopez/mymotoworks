"""The Flask side: one blueprint per area (pages + JSON API), kept thin. A route reads the
request, calls a service, and returns JSON or a page; errors from services become JSON answers
(mymotoworks.errors)."""

from mymotoworks.web import accounts, auth, backup, dashboard, items, reports, restocks, sales, stock

BLUEPRINTS = [auth.bp, backup.bp, dashboard.bp, accounts.bp, items.bp, reports.bp, restocks.bp, sales.bp, stock.bp]
