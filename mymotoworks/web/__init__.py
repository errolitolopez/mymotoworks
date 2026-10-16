"""The Flask side: one blueprint per area (pages + JSON API), kept thin. A route reads the
request, calls a service, and returns JSON or a page; errors from services become JSON answers
(mymotoworks.errors)."""

from mymotoworks.web import pages

BLUEPRINTS = [pages.bp]
