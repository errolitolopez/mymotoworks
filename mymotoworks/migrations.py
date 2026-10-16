"""Upgrading a database made by an older version of the app. schema.sql only creates tables that
do not exist yet, so a column added later has to be added here for databases that already have the
table. Safe to run on every start."""

# (table, column, definition). Each is added only when the table lacks it.
ADDED_COLUMNS = [
    ("sales", "note", "TEXT NOT NULL DEFAULT ''"),
    ("sales", "replaces_sale_id", "INTEGER REFERENCES sales(id)"),
]


def add_missing_columns(db):
    for table, column, definition in ADDED_COLUMNS:
        existing = [row["name"] for row in db.execute(f"PRAGMA table_info({table})")]
        # An empty list means the table does not exist: schema.sql has just created it complete.
        if existing and column not in existing:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    db.commit()
