"""Rules for reports: reading the month or year that was asked for."""

import calendar
import re

from mymotoworks.errors import ValidationError

MIN_YEAR = 2000
MAX_YEAR = 2100
MONTH_PATTERN = re.compile(r"\d{4}-\d{2}")
YEAR_PATTERN = re.compile(r"\d{4}")


def parse_month(text, default):
    """"2026-10" -> (2026, 10). An empty or missing text means `default` (a (year, month)). Raises
    ValidationError for anything else, so a bad value never reaches the SQL."""
    if text in (None, ""):
        return default
    if not isinstance(text, str) or not MONTH_PATTERN.fullmatch(text):
        raise ValidationError("Month must look like 2026-10.")
    year, month = int(text[:4]), int(text[5:])
    if not MIN_YEAR <= year <= MAX_YEAR or not 1 <= month <= 12:
        raise ValidationError("Month must look like 2026-10.")
    return year, month


def parse_year(text, default):
    """"2026" -> 2026. An empty or missing text means `default`."""
    if text in (None, ""):
        return default
    if not isinstance(text, str) or not YEAR_PATTERN.fullmatch(text) or not MIN_YEAR <= int(text) <= MAX_YEAR:
        raise ValidationError("Year must look like 2026.")
    return int(text)


def month_range(year, month):
    """(2026, 10) -> ("2026-10-01", "2026-10-31"): the first and last day, as ISO text."""
    last = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last:02d}"
