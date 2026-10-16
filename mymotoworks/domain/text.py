"""Small text helpers shared by the rules."""

from mymotoworks.errors import ValidationError


def like_pattern(text):
    """"50%" -> "%50\\%%": a LIKE pattern that matches the text as typed, so % and _ are plain
    characters. Use it with ESCAPE '\\'."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def clean_text(value, label, max_length, required=True):
    """"  AIR   FILTER " -> "AIR FILTER". Raises ValidationError when empty (if required) or too long."""
    text = " ".join(str(value or "").split())
    if required and not text:
        raise ValidationError(f"{label} is required.")
    if len(text) > max_length:
        raise ValidationError(f"{label} can be at most {max_length} characters.")
    return text
