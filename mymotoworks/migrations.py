"""Upgrading a database made by an older version of the app. schema.sql only creates tables that
do not exist yet, so a column added later has to be added here for databases that already have the
table. Safe to run on every start."""

# (table, column, definition, SQL to run once, right after the column is added or None).
ADDED_COLUMNS = [
    ("sales", "note", "TEXT NOT NULL DEFAULT ''", None),
    ("sales", "replaces_sale_id", "INTEGER REFERENCES sales(id)", None),
    ("sales", "approved_by", "INTEGER REFERENCES users(id)", None),
    # Sales made before approval existed already took their stock, so they count as approved.
    ("sales", "approved_at", "TEXT",
     "UPDATE sales SET approved_at = created_at, approved_by = user_id WHERE approved_at IS NULL"),
]


def add_missing_columns(db):
    for table, column, definition, after in ADDED_COLUMNS:
        existing = [row["name"] for row in db.execute(f"PRAGMA table_info({table})")]
        # An empty list means the table does not exist: schema.sql has just created it complete.
        if existing and column not in existing:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            if after:
                db.execute(after)
    db.commit()
