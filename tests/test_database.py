"""The tables, the default admin, and init-db."""

import sqlite3

import pytest
from werkzeug.security import check_password_hash

from mymotoworks.database import get_db


def admin_rows(app):
    with app.app_context():
        return get_db().execute("SELECT * FROM users WHERE role = 'admin'").fetchall()


def test_default_admin_exists_and_must_change_password(app):
    rows = admin_rows(app)
    assert len(rows) == 1
    admin = rows[0]
    assert admin["username"] == "admin"
    assert check_password_hash(admin["password_hash"], "admin")
    assert admin["must_change_password"] == 1
    assert admin["active"] == 1


def test_init_db_twice_keeps_one_admin(app):
    runner = app.test_cli_runner()
    assert runner.invoke(args=["init-db"]).exit_code == 0
    assert runner.invoke(args=["init-db"]).exit_code == 0
    assert len(admin_rows(app)) == 1


def test_username_is_unique_ignoring_capitals(app):
    with app.app_context():
        db = get_db()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO users (name, username, password_hash, role) "
                       "VALUES ('Other', 'Admin', 'x', 'staff')")


def test_role_must_be_admin_or_staff(app):
    with app.app_context():
        db = get_db()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO users (name, username, password_hash, role) "
                       "VALUES ('Teacher', 'teacher1', 'x', 'teacher')")
