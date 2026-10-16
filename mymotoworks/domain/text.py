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


MAX_SEARCH_WORDS = 6


def search_words(text):
    """"  air   NMAX " -> ["air", "NMAX"]. Each word must match, in any order, so "air nmax" finds
    "AIR FILTER SUNTAL" for NMAX V1. More than MAX_SEARCH_WORDS words are cut, so a very long
    search cannot make a very long query."""
    return str(text or "").split()[:MAX_SEARCH_WORDS]
