"""Backups: a complete copy of the data, the download, the console command and the reminder."""

import sqlite3
from datetime import datetime, timedelta, timezone

from conftest import db_execute, db_query, flask_app, login, make_item


def open_copy(tmp_path, data):
    path = tmp_path / "copy.db"
    path.write_bytes(data)
    return sqlite3.connect(path)


def test_the_download_is_a_complete_valid_copy(admin, tmp_path):
    make_item(admin, name="AIR FILTER SUNTAL", stock=3)
    response = admin.get("/backup/download")
    assert response.status_code == 200
    assert response.mimetype == "application/vnd.sqlite3"
    assert 'filename="mymotoworks-backup-' in response.headers["Content-Disposition"]
    assert response.headers["Cache-Control"] == "no-store"
    copy = open_copy(tmp_path, response.data)
    assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert copy.execute("SELECT name, stock FROM items").fetchall() == [("AIR FILTER SUNTAL", 3)]
    assert copy.execute("SELECT username FROM users ORDER BY id").fetchall() == [("admin",), ("staff1",)]


def test_the_download_is_for_the_admin_only(admin, client):
    assert login("staff1").get("/backup/download").status_code == 403
    assert client.get("/backup/download").status_code == 401


def test_later_writes_do_not_leak_into_a_copy_already_taken(admin, tmp_path):
    item = make_item(admin, stock=1000)
    data = admin.get("/backup/download").data
    for _ in range(20):
        admin.post("/api/stock-adjustments", json={"reason": "lost", "lines": [{"item_id": item["id"], "change": -1}]})
    assert open_copy(tmp_path, data).execute("SELECT stock FROM items").fetchone()[0] == 1000
    assert db_query("SELECT stock FROM items")[0]["stock"] == 980


def last_backup_text(client):
    return client.get("/dashboard").get_data(as_text=True)


def test_home_says_there_was_never_a_backup_then_today(admin):
    html = last_backup_text(admin)
    assert "Last backup: never" in html and "backup-warning" in html
    admin.get("/backup/download")
    html = last_backup_text(admin)
    assert "Last backup: today" in html and "backup-warning" not in html


def test_home_warns_when_the_last_backup_is_old(admin):
    old = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    db_execute("INSERT INTO settings (key, value) VALUES ('last_backup_at', ?)", (old,))
    html = last_backup_text(admin)
    assert "Last backup: 10 days ago" in html and "backup-warning" in html
    recent = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
    db_execute("UPDATE settings SET value = ? WHERE key = 'last_backup_at'", (recent,))
    html = last_backup_text(admin)
    assert "Last backup: 3 days ago" in html and "backup-warning" not in html


def test_the_backup_card_is_for_the_admin_only(admin):
    assert 'href="/backup/download"' in last_backup_text(admin)
    assert "Last backup" not in login("staff1").get("/dashboard").get_data(as_text=True)


def test_the_console_command_writes_a_backup_and_keeps_only_the_newest(admin, tmp_path):
    make_item(admin, stock=3)
    runner = flask_app.test_cli_runner()
    folder = tmp_path / "backups"
    for _ in range(4):
        result = runner.invoke(args=["backup", "--to", str(folder), "--keep", "2"])
        assert result.exit_code == 0, result.output
    names = sorted(path.name for path in folder.iterdir())
    assert len(names) == 2 and all(name.startswith("mymotoworks-") and name.endswith(".db") for name in names)
    copy = sqlite3.connect(folder / names[-1])
    assert copy.execute("SELECT stock FROM items").fetchone()[0] == 3
    assert "Last backup: today" in last_backup_text(admin)


def test_two_backups_in_the_same_second_have_different_names():
    from mymotoworks.backup import backup_name
    first, second = backup_name(), backup_name()
    assert first != second and first < second


def test_pruning_never_touches_other_files(tmp_path):
    from mymotoworks.backup import prune
    for name in ("mymotoworks-2026-10-01-000000-000000.db", "mymotoworks-2026-10-02-000000-000000.db",
                 "mymotoworks-2026-10-03-000000-000000.db", "notes.txt", "other.db"):
        (tmp_path / name).write_text("x")
    removed = prune(str(tmp_path), keep=1)
    assert removed == ["mymotoworks-2026-10-01-000000-000000.db", "mymotoworks-2026-10-02-000000-000000.db"]
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "mymotoworks-2026-10-03-000000-000000.db", "notes.txt", "other.db"]


def test_the_command_refuses_a_bad_keep_number(admin, tmp_path):
    result = flask_app.test_cli_runner().invoke(args=["backup", "--to", str(tmp_path), "--keep", "0"])
    assert result.exit_code != 0
