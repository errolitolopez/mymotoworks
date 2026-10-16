"""Admin use cases: list, create and change accounts."""

from werkzeug.security import generate_password_hash

from mymotoworks.domain.accounts import clean_name, clean_role, clean_username, make_temp_password
from mymotoworks.domain.text import like_pattern
from mymotoworks.errors import NotFoundError, ValidationError
from mymotoworks.services.base import Service
from mymotoworks.services.presenters import account_json


class AccountService(Service):
    def list(self, query=""):
        """Accounts whose name or username contains the text, by name."""
        rows = self.users.search(like_pattern(str(query or "").strip()))
        return {"users": [account_json(row) for row in rows]}

    def create(self, data):
        """A new account with a temporary password. Returns (account, the password, shown once)."""
        name = clean_name(data.get("name"))
        username = clean_username(data.get("username"))
        role = clean_role(data.get("role"))
        if self.users.username_taken(username):
            raise ValidationError("That username is taken.")
        temp_password = make_temp_password()
        user_id = self.users.create(name, username, generate_password_hash(temp_password), role, True)
        self.commit()
        return account_json(self.users.get(user_id)), temp_password

    def update(self, user_id, data):
        """Rename, activate or deactivate, and/or make a new temporary password.
        Returns (account, the new password or None)."""
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("Account not found.")
        if "name" in data:
            self.users.set_name(user_id, clean_name(data["name"]))
        if "active" in data:
            active = bool(data["active"])
            # An admin who deactivates themselves would be locked out with nobody to undo it.
            if not active and user_id == self.user["id"]:
                raise ValidationError("You can't deactivate your own account.")
            self.users.set_active(user_id, active)
        temp_password = None
        if data.get("reset_password"):
            temp_password = make_temp_password()
            self.users.set_password(user_id, generate_password_hash(temp_password), True)
        self.commit()
        return account_json(self.users.get(user_id)), temp_password
