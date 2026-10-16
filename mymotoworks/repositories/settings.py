"""SQL for the settings table (shop-wide values). It never commits: the service does."""

from mymotoworks.repositories.base import Repository


class SettingsRepository(Repository):
    def get(self, key):
        row = self.one("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else None

    def put(self, key, value):
        self.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value))
