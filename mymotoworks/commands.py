"""Command-line tools for the person who runs the server (not part of the web app)."""

import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from mymotoworks.database import get_db
from mymotoworks.domain.accounts import check_password_change
from mymotoworks.errors import ValidationError
from mymotoworks.repositories import UserRepository


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
