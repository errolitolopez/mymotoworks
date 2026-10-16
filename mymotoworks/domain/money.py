"""Limits and checks for money (whole centavos) and counts (stock, re-order)."""

from mymotoworks.errors import ValidationError

MAX_CENTAVOS = 100_000_000  # 1,000,000 pesos
MAX_COUNT = 1_000_000


def _whole_number(value):
    """True for a real integer. bool is an int in Python, but `true` is not an amount."""
    return isinstance(value, int) and not isinstance(value, bool)


def check_centavos(value, label):
    """The amount in whole centavos. Raises ValidationError unless it is an integer from 0 to MAX_CENTAVOS."""
    if not _whole_number(value) or not 0 <= value <= MAX_CENTAVOS:
        raise ValidationError(f"{label} must be an amount from 0 to {MAX_CENTAVOS // 100:,} pesos.")
    return value


def check_count(value, label):
    """A stock or re-order number. Raises ValidationError unless it is an integer from 0 to MAX_COUNT."""
    if not _whole_number(value) or not 0 <= value <= MAX_COUNT:
        raise ValidationError(f"{label} must be a whole number from 0 to {MAX_COUNT}.")
    return value
