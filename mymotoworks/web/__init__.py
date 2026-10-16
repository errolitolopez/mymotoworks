"""The Flask side: one blueprint per area (pages + JSON API), kept thin. A route reads the
request, calls a service, and returns JSON or a page; errors from services become JSON answers
(mymotoworks.errors)."""

from mymotoworks.web import accounts, auth, dashboard, items

BLUEPRINTS = [auth.bp, dashboard.bp, accounts.bp, items.bp]
