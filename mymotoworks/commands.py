"""Command-line tools for the person who runs the server (not part of the web app)."""

import os

import click
from flask import current_app
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from mymotoworks import backup
from mymotoworks.database import get_db
from mymotoworks.domain.accounts import check_password_change
from mymotoworks.errors import ValidationError
from mymotoworks.repositories import UserRepository
from mymotoworks.services import BackupService


@click.command("set-password")
@click.argument("username")
@with_appcontext
def set_password_command(username):
    """Set a new password for USERNAME. It is asked twice and never shown.

    Use it on a new server before the site is reachable, and when the admin forgot the password."""
    db = get_db()
    users = UserRepository(db)
    user = users.by_username(username)
    if user is None:
        raise click.ClickException("There is no user with that username.")
    password = click.prompt("New password", hide_input=True, confirmation_prompt=True)
    try:
        # Same rules as the change-password page. The current password is empty: the person is the server's owner.
        check_password_change(user["username"], "", password)
    except ValidationError as error:
        raise click.ClickException(error.message) from None
    # False: no forced change at the next login, since the owner just chose this password.
    users.set_password(user["id"], generate_password_hash(password), False)
    db.commit()
    click.echo(f"Password set for {user['username']}.")


DEFAULT_KEEP = 14


@click.command("backup")
@click.option("--to", "folder", default=None, help="Folder for the backup (default: instance/backups).")
@click.option("--keep", default=DEFAULT_KEEP, show_default=True, help="How many backups to keep. Older ones are deleted.")
@with_appcontext
def backup_command(folder, keep):
    """Write a complete copy of the database to a new file, and delete the oldest copies."""
    if keep < 1:
        raise click.ClickException("--keep must be 1 or more.")
    folder = folder or os.path.join(current_app.instance_path, "backups")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, backup.backup_name())
    backup.backup_to(current_app.config["DATABASE"], path)
    db = get_db()
    BackupService(db).record()
    db.commit()
    removed = backup.prune(folder, keep)
    click.echo(f"Backup written to {path}" + (f" ({len(removed)} old ones deleted)." if removed else "."))
