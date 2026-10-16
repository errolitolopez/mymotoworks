"""Rules for restocks: checking what the restock page sends."""

from mymotoworks.domain.money import check_centavos, is_whole_number
from mymotoworks.domain.sales import clean_date
from mymotoworks.domain.text import clean_text
from mymotoworks.errors import ValidationError

MAX_LINES = 100
MAX_QTY = 100_000
MAX_NOTE_LENGTH = 200
MAX_REF_LENGTH = 64


def _clean_line(line):
    if not isinstance(line, dict):
        raise ValidationError("Add at least one item.")
    item_id = line.get("item_id")
    # An id that is not a whole number matches no item: say so the same way as an unknown item.
    if not is_whole_number(item_id) or item_id < 1:
        raise ValidationError("An item in the list does not exist.")
    qty = line.get("qty")
    if not is_whole_number(qty) or not 1 <= qty <= MAX_QTY:
        raise ValidationError(f"Quantity must be a whole number from 1 to {MAX_QTY}.")
    puhunan = line.get("puhunan")
    # No cost sent means "keep the item's current cost".
    return {"item_id": item_id, "qty": qty, "puhunan": None if puhunan is None else check_centavos(puhunan, "Cost")}


def clean_restock(data, today):
    """What the restock page sent, checked: {"restock_date", "client_ref", "note", "lines"}. `today` is
    the shop's date. A past day is allowed, a future day is not. Each item may be listed only once."""
    lines = data.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ValidationError("Add at least one item.")
    if len(lines) > MAX_LINES:
        raise ValidationError(f"A restock can have at most {MAX_LINES} items.")
    cleaned = [_clean_line(line) for line in lines]
    ids = [line["item_id"] for line in cleaned]
    if len(set(ids)) != len(ids):
        raise ValidationError("An item is listed twice.")

    restock_date = data.get("restock_date")
    if restock_date in (None, ""):
        day = today
    else:
        day = clean_date(restock_date)
        if day > today:
            raise ValidationError("The date can't be in the future.")

    note = data.get("note")
    if note is not None and not isinstance(note, str):
        raise ValidationError("Note must be text.")
    client_ref = data.get("client_ref")
    if client_ref is not None and (not isinstance(client_ref, str) or not client_ref
                                   or len(client_ref) > MAX_REF_LENGTH):
        raise ValidationError("That restock reference is not valid.")
    return {"restock_date": day.isoformat(), "client_ref": client_ref, "lines": cleaned,
            "note": clean_text(note, "Note", MAX_NOTE_LENGTH, required=False)}
