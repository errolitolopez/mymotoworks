"""flask --app app seed: sample items so the Items page can be tried without typing 100 of them."""

import click
from flask.cli import with_appcontext

from mymotoworks.database import get_db

# (name, [models]): every model becomes one item. Prices are made up.
SAMPLES = [
    ("AIR FILTER SUNTAL", ["MIOi125 M3", "NMAX V1", "CLICK125", "MIO SOUL", "MIO AMORE"]),
    ("SPARK PLUG NGK", ["C7HSA", "CR7HSA", "CPR8EA-9", "CR6HSA"]),
    ("BRAKE PAD", ["MIO SOUL", "CLICK125", "NMAX V1", "BEAT", "RAIDER150", "XRM125"]),
    ("DRIVE BELT", ["MIO SOUL", "CLICK125", "NMAX V1", "BEAT", "AEROX"]),
    ("BEARING", ["6004 2RS", "6203 2RS", "6301 2RS", "6000 2RS", "6201 2RS"]),
    ("GEAR OIL 100ML", ["KAWASAKI", "YAMAHA", "HONDA", "SHELL"]),
    ("ENGINE OIL 1L", ["MOTUL SCOOTER 10W-40", "SHELL AX5 800ML", "PETRON SPRINT 4T", "CASTROL POWER1"]),
    ("BULB", ["S25", "T10", "H4", "HS1", "M5"]),
    ("CHAIN SET", ["428-120L", "428-124L", "415-110L", "420-120L"]),
    ("CABLE", ["THROTTLE", "CLUTCH", "BRAKE", "SPEEDOMETER"]),
]
COPIES = 3  # each name + model made a few times with different part numbers, to fill several pages


def seed_items(db):
    """Add the sample items. Safe to run again: it does nothing when items already exist."""
    if db.execute("SELECT 1 FROM items LIMIT 1").fetchone():
        return 0
    rows = []
    for name, models in SAMPLES:
        for model_number, model in enumerate(models):
            for copy in range(COPIES):
                puhunan = 2000 + 350 * model_number + 100 * copy  # centavos
                rows.append((name, model, f"{name[:2]}{model_number}{copy}", puhunan,
                             puhunan * 2, 2 + (model_number + copy) % 6, 2))
    db.executemany(
        "INSERT INTO items (name, model, part_no, puhunan, benta, stock, reorder_level) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    db.commit()
    return len(rows)


@click.command("seed")
@with_appcontext
def seed_command():
    """Add sample items (only when there are none)."""
    added = seed_items(get_db())
    click.echo(f"Added {added} sample items." if added else "Items already exist: nothing added.")
