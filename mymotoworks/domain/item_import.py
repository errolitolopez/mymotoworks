"""Rules for the one-time import of items from the old spreadsheet."""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from mymotoworks.domain.items import clean_item
from mymotoworks.errors import ValidationError

# The old sheet has no real re-order numbers (its RE-ORDER column is restocked quantity), so every
# imported item starts at 0 and the owner sets real levels later.
IMPORT_REORDER_LEVEL = 0


@dataclass
class ImportPlan:
    """What the import would do: the items to add, the rows skipped, and notes for the owner."""
    rows_read: int = 0
    items: list = field(default_factory=list)      # (row number, fields for ItemRepository.create)
    problems: list = field(default_factory=list)   # (row number, reason)
    warnings: list = field(default_factory=list)   # plain sentences
    no_puhunan: int = 0                            # items imported with a cost of 0
    existing: int = 0                              # items already in the database


def cell_text(value):
    """12 -> "12", 39103519.0 -> "39103519", " AIR  FILTER " -> "AIR FILTER", None -> ""."""
    if value is None:
        return ""
    # Excel stores whole numbers as floats; "39103519.0" would be a wrong part number.
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return " ".join(str(value).split())


def _decimal(value, label):
    """The exact number in a cell. Raises ValidationError when it is not a number."""
    if isinstance(value, bool):
        raise ValidationError(f"{label} is not a number: {value}.")
    # Decimal(str(x)) keeps what Excel shows (133.2), unlike Decimal(float) which keeps the noise.
    text = cell_text(value).replace(",", "").replace("₱", "")
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise ValidationError(f"{label} is not a number: {cell_text(value)}.") from None
    if not number.is_finite():
        raise ValidationError(f"{label} is not a number: {cell_text(value)}.")
    return number


def _centavos(value, label):
    return int((_decimal(value, label) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _count(value, label):
    number = _decimal(value, label)
    if number != number.to_integral_value():
        raise ValidationError(f"{label} must be a whole number, not {cell_text(value)}.")
    return int(number)


def clean_import_row(record):
    """The fields of one spreadsheet row, ready for ItemRepository.create. Raises ValidationError
    with the reason when the row cannot be imported. A missing puhunan or stock counts as 0."""
    if cell_text(record["benta"]) == "":
        raise ValidationError("Benta (price) is missing.")
    puhunan = 0 if cell_text(record["puhunan"]) == "" else _centavos(record["puhunan"], "Puhunan")
    stock = 0 if cell_text(record["stock"]) == "" else _count(record["stock"], "Stock")
    return clean_item({
        "name": cell_text(record["name"]),
        "model": cell_text(record["model"]),
        "part_no": cell_text(record["part_no"]),
        "puhunan": puhunan,
        "benta": _centavos(record["benta"], "Benta"),
        "stock": stock,
        "reorder_level": IMPORT_REORDER_LEVEL,
        "track_stock": True,
    }, creating=True)


def build_plan(rows):
    """Clean every row. `rows` is a list of (row number, record). Rows that are completely empty
    are ignored; rows with a problem go to `problems` and are not imported."""
    plan = ImportPlan()
    first_row_of = {}  # (name, model, part no) in capitals -> first row number
    for number, record in rows:
        if all(cell_text(value) == "" for value in record.values()):
            continue
        plan.rows_read += 1
        try:
            fields = clean_import_row(record)
        except ValidationError as error:
            plan.problems.append((number, error.message))
            continue
        key = (fields["name"].upper(), fields["model"].upper(), fields["part_no"].upper())
        if key in first_row_of:
            plan.warnings.append(f"Row {number} looks the same as row {first_row_of[key]}: {fields['name']}.")
        else:
            first_row_of[key] = number
        if cell_text(record["puhunan"]) == "":
            plan.no_puhunan += 1
        plan.items.append((number, fields))
    return plan
