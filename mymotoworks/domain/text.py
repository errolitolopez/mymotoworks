"""Small text helpers shared by the rules."""


def like_pattern(text):
    """"50%" -> "%50\\%%": a LIKE pattern that matches the text as typed, so % and _ are plain
    characters. Use it with ESCAPE '\\'."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
