"""Rules for sales: checking what the cart sends."""

import re
from datetime import date

from mymotoworks.domain.money import check_centavos, is_whole_number
from mymotoworks.errors import ValidationError

MAX_LINES = 50
MAX_QTY = 1000
MAX_REF_LENGTH = 64
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


def clean_date(value):
    """"2026-10-16" -> date(2026, 10, 16). Raises ValidationError for anything else. Only this exact
    shape is accepted, so a date means the same thing everywhere."""
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        raise ValidationError("Date must look like 2026-10-16.")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValidationError("Date must look like 2026-10-16.") from None


def _clean_line(line):
    if not isinstance(line, dict):
        raise ValidationError("Add at least one item.")
    item_id = line.get("item_id")
    # An id that is not a whole number matches no item: say so the same way as an unknown item.
    if not is_whole_number(item_id) or item_id < 1:
        raise ValidationError("An item in the cart does not exist.")
    qty = line.get("qty")
    if not is_whole_number(qty) or not 1 <= qty <= MAX_QTY:
        raise ValidationError(f"Quantity must be a whole number from 1 to {MAX_QTY}.")
    benta = line.get("benta")
    # No price sent means "use the item's own price".
    return {"item_id": item_id, "qty": qty, "benta": None if benta is None else check_centavos(benta, "Price")}


def clean_sale(data, today, is_admin):
    """What the cart sent, checked: {"sale_date", "client_ref", "lines"}. `today` is the shop's date.
    Staff may only sell today; the admin may also use a past day. Nobody may use a future day."""
    lines = data.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ValidationError("Add at least one item.")
    if len(lines) > MAX_LINES:
        raise ValidationError(f"A sale can have at most {MAX_LINES} items.")
    cleaned = [_clean_line(line) for line in lines]

    sale_date = data.get("sale_date")
    if sale_date in (None, ""):
        day = today
    else:
        day = clean_date(sale_date)
        if day > today:
            raise ValidationError("The date can't be in the future.")
        if day != today and not is_admin:
            raise ValidationError("Staff can only record today's sales.")

    client_ref = data.get("client_ref")
    if client_ref is not None and (not isinstance(client_ref, str) or not client_ref
                                   or len(client_ref) > MAX_REF_LENGTH):
        raise ValidationError("That sale reference is not valid.")
    return {"sale_date": day.isoformat(), "client_ref": client_ref, "lines": cleaned}
