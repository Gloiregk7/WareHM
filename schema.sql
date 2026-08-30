-- Drop existing tables if they exist
DROP TABLE IF EXISTS audit_trail;
DROP TABLE IF EXISTS pick_alerts;
DROP TABLE IF EXISTS staff_performance;
DROP TABLE IF EXISTS verification_log;
DROP TABLE IF EXISTS staff;
DROP TABLE IF EXISTS hospitals;
DROP TABLE IF EXISTS supervisors;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS inventory;

-- Inventory Table
CREATE TABLE inventory (
    inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE,
    item_name TEXT NOT NULL,
    batch_code TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    location TEXT NOT NULL,
    expiry_date TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Staff Table
CREATE TABLE staff (
    staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operator_name TEXT NOT NULL,
    employee_id TEXT NOT NULL UNIQUE,
    department TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'warehouse_staff',
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Hospital Accounts
CREATE TABLE hospitals (
    hospital_id INTEGER PRIMARY KEY AUTOINCREMENT,
    hospital_name TEXT NOT NULL,
    hospital_code TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Supervisor Accounts
CREATE TABLE supervisors (
    supervisor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    supervisor_name TEXT NOT NULL,
    supervisor_code TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Orders Table
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL,
    item_name TEXT NOT NULL,
    target_batch TEXT NOT NULL,
    required_quantity INTEGER NOT NULL DEFAULT 1,
    expiry_date TEXT NOT NULL,
    location TEXT NOT NULL,
    destination TEXT NOT NULL,
    dispatcher_name TEXT NOT NULL,
    hospital_id INTEGER,
    status TEXT NOT NULL DEFAULT 'PENDING',
    assigned_to INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (assigned_to) REFERENCES staff(staff_id),
    FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id)
);

-- Verification Log Table (Audit Trail Core)
CREATE TABLE verification_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    sku TEXT NOT NULL,
    scanned_batch TEXT NOT NULL,
    scanned_expiry TEXT NOT NULL,
    result TEXT NOT NULL,
    error_codes TEXT,
    operator_id INTEGER,
    station_id TEXT,
    verification_time REAL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (operator_id) REFERENCES staff(staff_id)
);

-- Audit Trail Table (Comprehensive)
CREATE TABLE audit_trail (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    staff_id INTEGER,
    order_id INTEGER,
    old_value TEXT,
    new_value TEXT,
    status TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (staff_id) REFERENCES staff(staff_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- Pick Alerts Table
CREATE TABLE pick_alerts (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    alert_type TEXT NOT NULL,
    alert_code TEXT NOT NULL,
    alert_message TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'HIGH',
    alert_status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- Staff Performance Table
CREATE TABLE staff_performance (
    performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id INTEGER NOT NULL,
    total_picks INTEGER DEFAULT 0,
    successful_picks INTEGER DEFAULT 0,
    failed_picks INTEGER DEFAULT 0,
    accuracy_rate REAL DEFAULT 0.0,
    average_pick_time REAL DEFAULT 0.0,
    last_updated TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (staff_id) REFERENCES staff(staff_id)
);

-- Create Indexes for Performance
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_verification_result ON verification_log(result);
CREATE INDEX idx_audit_action ON audit_trail(action);
CREATE INDEX idx_staff_employee ON staff(employee_id);
CREATE INDEX idx_alert_order ON pick_alerts(order_id);
CREATE INDEX idx_performance_staff ON staff_performance(staff_id);