"""Rules for accounts: names, usernames, passwords."""

from mymotoworks.errors import ValidationError

MIN_PASSWORD_LENGTH = 6


def check_password_change(username, current_password, new_password):
    """Raise ValidationError unless the new password is allowed. Spaces are part of a password."""
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"New password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if new_password == current_password:
        raise ValidationError("Choose a different password from the current one.")
    if new_password.lower() == username.lower():
        raise ValidationError("The password can't be your username.")
