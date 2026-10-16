"""SQL for the users table. It never commits: the service does."""

from mymotoworks.repositories.base import Repository


class UserRepository(Repository):
    def has_admin(self):
        """True when at least one admin account exists."""
        return self.one("SELECT 1 FROM users WHERE role = 'admin'") is not None

    def create(self, name, username, password_hash, role, must_change_password):
        """Add a user and return its id."""
        cursor = self.execute(
            "INSERT INTO users (name, username, password_hash, role, must_change_password) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, username, password_hash, role, must_change_password),
        )
        return cursor.lastrowid
