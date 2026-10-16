"""Login and password use cases."""

from werkzeug.security import check_password_hash

from mymotoworks.errors import ForbiddenError, UnauthorizedError, ValidationError
from mymotoworks.services.base import Service


class AuthService(Service):
    def login(self, username, password):
        """The user's row when the username and password are right."""
        # str() so a number or list sent as JSON gives a normal "wrong password", not a crash.
        username = str(username or "").strip()
        # The password is never trimmed: spaces may be part of it.
        password = str(password or "")
        if not username or not password:
            raise ValidationError("Enter your username and password.")
        user = self.users.by_username(username)
        # Same message for an unknown user and a wrong password, so nobody can find out
        # which usernames exist.
        if user is None or not check_password_hash(user["password_hash"], password):
            raise UnauthorizedError("Wrong username or password.")
        if not user["active"]:
            raise ForbiddenError("This account is deactivated. Ask the admin.")
        return user
