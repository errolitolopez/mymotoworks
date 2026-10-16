"""Rules for accounts: names, usernames, passwords."""

import re
import secrets

from mymotoworks.errors import ValidationError

MIN_PASSWORD_LENGTH = 6
ROLES = ("admin", "staff")
USERNAME_PATTERN = re.compile(r"[a-z0-9._-]{3,30}")
MAX_NAME_LENGTH = 100
# Temporary passwords leave out letters and digits that look alike (l, 1, o, 0).
TEMP_PASSWORD_LETTERS = "abcdefghjkmnpqrstuvwxyz23456789"
TEMP_PASSWORD_LENGTH = 10


def check_password_change(username, current_password, new_password):
    """Raise ValidationError unless the new password is allowed. Spaces are part of a password."""
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"New password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if new_password == current_password:
        raise ValidationError("Choose a different password from the current one.")
    if new_password.lower() == username.lower():
        raise ValidationError("The password can't be your username.")


def make_temp_password():
    return "".join(secrets.choice(TEMP_PASSWORD_LETTERS) for _ in range(TEMP_PASSWORD_LENGTH))


def clean_name(value):
    """"  Maria   Santos " -> "Maria Santos". Raises ValidationError when empty or too long."""
    name = " ".join(str(value or "").split())
    if not name:
        raise ValidationError("Name is required.")
    if len(name) > MAX_NAME_LENGTH:
        raise ValidationError(f"Name can be at most {MAX_NAME_LENGTH} characters.")
    return name


def clean_username(value):
    """" Staff1 " -> "staff1". Raises ValidationError when it has other characters or a bad length."""
    username = str(value or "").strip().lower()
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValidationError("Username must be 3 to 30 letters, numbers, dots, dashes or underscores.")
    return username


def clean_role(value):
    """"admin" or "staff". Raises ValidationError for anything else."""
    if value not in ROLES:
        raise ValidationError("Choose a role: admin or staff.")
    return value
