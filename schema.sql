DROP TABLE IF EXISTS verification_log;
DROP TABLE IF EXISTS orders;

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL,
    item_name TEXT NOT NULL,
    target_batch TEXT NOT NULL,
    expiry_date TEXT NOT NULL,
    location TEXT NOT NULL,
    destination TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE verification_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    sku TEXT NOT NULL,
    scanned_batch TEXT NOT NULL,
    scanned_expiry TEXT NOT NULL,
    result TEXT NOT NULL,
    error_codes TEXT,
    operator TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);