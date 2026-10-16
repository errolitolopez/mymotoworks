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

    def get_active(self, user_id):
        """The user, or None if there is no such user or the account is deactivated."""
        return self.one("SELECT * FROM users WHERE id = ? AND active = 1", (user_id,))

    def by_username(self, username):
        """The user with this username (capitals do not matter), or None."""
        return self.one("SELECT * FROM users WHERE username = ?", (username,))

    def set_password(self, user_id, password_hash, must_change_password):
        self.execute("UPDATE users SET password_hash = ?, must_change_password = ? WHERE id = ?",
                     (password_hash, 1 if must_change_password else 0, user_id))

    def get(self, user_id):
        return self.one("SELECT * FROM users WHERE id = ?", (user_id,))

    def username_taken(self, username):
        return self.one("SELECT 1 FROM users WHERE username = ?", (username,)) is not None

    def search(self, pattern):
        """Users whose name or username contains the text (pattern from like_pattern), by name."""
        return self.all(
            "SELECT * FROM users WHERE name LIKE ? ESCAPE '\\' OR username LIKE ? ESCAPE '\\' "
            "ORDER BY name COLLATE NOCASE, username",
            (pattern, pattern),
        )

    def set_name(self, user_id, name):
        self.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))

    def set_active(self, user_id, active):
        self.execute("UPDATE users SET active = ? WHERE id = ?", (1 if active else 0, user_id))
