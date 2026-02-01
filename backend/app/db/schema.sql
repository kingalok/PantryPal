-- PantryPal SQLite schema (POC)

CREATE TABLE IF NOT EXISTS vendor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    base_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS product (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id INTEGER NOT NULL REFERENCES vendor(id),
    external_id TEXT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    image_url TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(vendor_id, external_id)
);

CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    alert_email TEXT,
    alert_telegram_chat_id TEXT,
    alert_on_drop_only INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    price REAL,
    nectar_price REAL,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alert (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    watchlist_id INTEGER NOT NULL REFERENCES watchlist(id) ON DELETE CASCADE,
    price_history_id INTEGER NOT NULL REFERENCES price_history(id),
    message TEXT NOT NULL,
    sent_at TEXT NOT NULL DEFAULT (datetime('now')),
    channel TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_price_history_product_recorded ON price_history(product_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_alert_watchlist ON alert(watchlist_id, price_history_id, channel);

-- Seed Sainsbury's vendor
INSERT OR IGNORE INTO vendor (id, name, slug, base_url, is_active) VALUES (1, 'Sainsbury''s', 'sainsburys', 'https://www.sainsburys.co.uk', 1);
