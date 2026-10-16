"""Backup use cases: remember when a backup was taken, and say how old the last one is."""

from datetime import datetime, timezone

from flask import current_app

from mymotoworks import backup
from mymotoworks.repositories import SettingsRepository
from mymotoworks.services.base import Service

LAST_BACKUP_KEY = "last_backup_at"
STALE_AFTER_DAYS = 7


def _now_text():
    """The current time as the database writes it: "2026-10-16 02:30:00" (UTC)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class BackupService(Service):
    def __init__(self, db, user=None):
        super().__init__(db, user)
        self.settings = SettingsRepository(db)

    def record(self):
        """Remember that a backup was just taken (no commit)."""
        self.settings.put(LAST_BACKUP_KEY, _now_text())

    def download(self):
        """A complete copy of the database as bytes, and a note that a backup was taken."""
        data = backup.backup_bytes(current_app.config["DATABASE"])
        self.record()
        self.commit()
        return data

    def status(self):
        """{"last", "days", "stale"}: when the last backup was (UTC text), how many days ago, and whether the
        owner should be reminded (never, or more than STALE_AFTER_DAYS days ago)."""
        text = self.settings.get(LAST_BACKUP_KEY)
        if text is None:
            return {"last": None, "days": None, "stale": True}
        taken = datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - taken).days
        return {"last": text, "days": days, "stale": days > STALE_AFTER_DAYS}
