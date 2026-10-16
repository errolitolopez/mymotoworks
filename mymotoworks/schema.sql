-- The tables. Safe to run again: existing data is kept.

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    -- NOCASE: "Admin" and "admin" are the same username
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'staff')),
    must_change_password INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Shop-wide values, e.g. the opening cash balance (added in the cash task)
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Parts, oils and services. Money is whole centavos (103.50 pesos = 10350).
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    part_no TEXT NOT NULL DEFAULT '',
    puhunan INTEGER NOT NULL DEFAULT 0 CHECK (puhunan >= 0),
    benta INTEGER NOT NULL CHECK (benta >= 0),
    stock INTEGER NOT NULL DEFAULT 0,
    reorder_level INTEGER NOT NULL DEFAULT 0,
    -- 0 for services and loose items (LINIS, GRASA): stock is never lowered or counted
    track_stock INTEGER NOT NULL DEFAULT 1,
    -- deactivated, never deleted, so old sales keep their history
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
