"""Rules for stock adjustments and recounts: checking what the pages send."""

from mymotoworks.domain.money import MAX_COUNT, check_count, is_whole_number
from mymotoworks.domain.text import clean_text
from mymotoworks.errors import ValidationError

# reason -> the label shown to people
REASONS = {
    "lost": "Lost",
    "missing": "Missing",
    "damaged": "Damaged",
    "count_correction": "Count correction",
    "other": "Other",
}
MAX_LINES = 100
MAX_NOTE_LENGTH = 200
MAX_REF_LENGTH = 64


def _item_id(line):
    item_id = line.get("item_id")
    # An id that is not a whole number matches no item: say so the same way as an unknown item.
    if not is_whole_number(item_id) or item_id < 1:
        raise ValidationError("An item in the list does not exist.")
    return item_id


def _lines(data, clean_line):
    lines = data.get("lines")
    if not isinstance(lines, list) or not lines or not all(isinstance(line, dict) for line in lines):
        raise ValidationError("Add at least one item.")
    if len(lines) > MAX_LINES:
        raise ValidationError(f"A save can have at most {MAX_LINES} items.")
    cleaned = [clean_line(line) for line in lines]
    ids = [line["item_id"] for line in cleaned]
    if len(set(ids)) != len(ids):
        raise ValidationError("An item is listed twice.")
    return cleaned


def _note_and_ref(data):
    note = data.get("note")
    if note is not None and not isinstance(note, str):
        raise ValidationError("Note must be text.")
    client_ref = data.get("client_ref")
    if client_ref is not None and (not isinstance(client_ref, str) or not client_ref
                                   or len(client_ref) > MAX_REF_LENGTH):
        raise ValidationError("That reference is not valid.")
    return clean_text(note, "Note", MAX_NOTE_LENGTH, required=False), client_ref


def _clean_change_line(line):
    item_id = _item_id(line)
    change = line.get("change")
    if not is_whole_number(change) or change == 0 or abs(change) > MAX_COUNT:
        raise ValidationError(f"Change must be a whole number, not 0, from -{MAX_COUNT} to {MAX_COUNT}.")
    return {"item_id": item_id, "change": change}


def clean_adjustment(data):
    """What the adjust form sent, checked: {"reason", "note", "client_ref", "lines": [{"item_id", "change"}]}.
    A change is negative to take out and positive to add. "Other" needs a note."""
    lines = _lines(data, _clean_change_line)
    reason = data.get("reason")
    if not isinstance(reason, str) or reason not in REASONS:
        raise ValidationError("Choose a reason.")
    note, client_ref = _note_and_ref(data)
    if reason == "other" and not note:
        raise ValidationError("Write a note when the reason is Other.")
    return {"reason": reason, "note": note, "client_ref": client_ref, "lines": lines}


def _clean_count_line(line):
    return {"item_id": _item_id(line), "counted": check_count(line.get("counted"), "Counted")}


def clean_count(data):
    """What the recount page sent, checked: {"note", "client_ref", "lines": [{"item_id", "counted"}]}.
    `counted` is what is really on the shelf, 0 or more."""
    lines = _lines(data, _clean_count_line)
    note, client_ref = _note_and_ref(data)
    return {"note": note, "client_ref": client_ref, "lines": lines}
