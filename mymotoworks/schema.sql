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

-- One row per customer. Never deleted: a wrong sale is voided, so history stays correct.
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_date TEXT NOT NULL,                 -- YYYY-MM-DD, the shop's day
    user_id INTEGER NOT NULL REFERENCES users(id),
    total INTEGER NOT NULL,                  -- centavos
    -- Made by the phone for each cart, so a double tap or a retry saves only once.
    client_ref TEXT UNIQUE,
    voided_at TEXT,
    voided_by INTEGER REFERENCES users(id),
    void_reason TEXT NOT NULL DEFAULT '',
    -- Free text such as the customer's name, so a sale can be found and tracked later.
    note TEXT NOT NULL DEFAULT '',
    -- Set when this sale corrects an earlier one: the earlier sale was voided and is kept as history.
    replaces_sale_id INTEGER REFERENCES sales(id),
    -- Every sale waits (approved_at is empty) and does not touch the stock until the admin approves it.
    approved_by INTEGER REFERENCES users(id),
    approved_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sales_date ON sales (sale_date);

-- The name and prices are copied when the sale is saved, so changing an item later never changes
-- an old sale.
CREATE TABLE IF NOT EXISTS sale_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL REFERENCES sales(id),
    item_id INTEGER NOT NULL REFERENCES items(id),
    item_name TEXT NOT NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),
    puhunan INTEGER NOT NULL,
    benta INTEGER NOT NULL,
    -- 1 when this line lowered the item's stock, so a void puts back exactly that
    tracked INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sale_lines_sale ON sale_lines (sale_id);

-- Goods that arrived. Never deleted: a wrong restock is voided, so history stays correct.
CREATE TABLE IF NOT EXISTS restocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restock_date TEXT NOT NULL,              -- YYYY-MM-DD, the shop's day
    user_id INTEGER NOT NULL REFERENCES users(id),
    total INTEGER NOT NULL,                  -- centavos
    note TEXT NOT NULL DEFAULT '',
    -- Made by the page for each restock, so a double tap or a retry saves only once.
    client_ref TEXT UNIQUE,
    voided_at TEXT,
    voided_by INTEGER REFERENCES users(id),
    void_reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_restocks_date ON restocks (restock_date);

-- The name and both costs are copied when the restock is saved. old_puhunan is what the item cost
-- before, so the history shows the change and a void can put it back.
CREATE TABLE IF NOT EXISTS restock_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restock_id INTEGER NOT NULL REFERENCES restocks(id),
    item_id INTEGER NOT NULL REFERENCES items(id),
    item_name TEXT NOT NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),
    puhunan INTEGER NOT NULL,                -- the new cost of one piece
    old_puhunan INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_restock_lines_restock ON restock_lines (restock_id);
