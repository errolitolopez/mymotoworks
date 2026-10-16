"""Rules for items: cleaning what the admin typed."""

from mymotoworks.domain.money import check_centavos, check_count
from mymotoworks.domain.text import clean_text

MAX_NAME_LENGTH = 120
MAX_MODEL_LENGTH = 60
MAX_PART_NO_LENGTH = 60


def clean_item(data, creating):
    """The item's fields, cleaned and checked. `data` has every field that is set (an edit merges
    the saved item with what changed first). Stock is only read when creating: after that it
    changes through sales, restocks and stock adjustments."""
    track_stock = bool(data.get("track_stock", True))
    fields = {
        "name": clean_text(data.get("name"), "Item name", MAX_NAME_LENGTH),
        "model": clean_text(data.get("model"), "Model", MAX_MODEL_LENGTH, required=False),
        "part_no": clean_text(data.get("part_no"), "Part no.", MAX_PART_NO_LENGTH, required=False),
        # A missing puhunan counts as 0 (services and loose items have no cost).
        "puhunan": check_centavos(data.get("puhunan", 0), "Puhunan"),
        "benta": check_centavos(data.get("benta"), "Benta"),
        "reorder_level": check_count(data.get("reorder_level", 0), "Re-order"),
        "track_stock": track_stock,
        "active": bool(data.get("active", True)),
    }
    if creating:
        fields["stock"] = check_count(data.get("stock", 0), "Stock")
        if not track_stock:
            # Untracked items have no count to keep.
            fields["stock"] = 0
            fields["reorder_level"] = 0
    return fields
