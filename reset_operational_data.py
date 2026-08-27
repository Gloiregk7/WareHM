import sqlite3

DB_NAME = 'kemsa_wms.db'

starter_inventory = [
    ('MED-601', 'Surgical Gloves', 'BATCH-2027F', 200, 'Shelf F1', '2027-09-30'),
    ('MED-602', 'Sterile Syringes 5ml', 'BATCH-2027G', 150, 'Shelf F2', '2027-12-31'),
    ('MED-603', 'Gauze Swabs 10cm', 'BATCH-2028H', 300, 'Shelf G1', '2028-03-31'),
    ('MED-604', 'Hand Sanitizer 500ml', 'BATCH-2027I', 100, 'Shelf G2', '2027-07-31'),
]

conn = sqlite3.connect(DB_NAME)
conn.execute('PRAGMA foreign_keys = ON')
conn.execute('DELETE FROM verification_log')
conn.execute('DELETE FROM audit_trail')
conn.execute('DELETE FROM pick_alerts')
conn.execute('DELETE FROM orders')
conn.execute('''
    UPDATE staff_performance
    SET total_picks = 0, successful_picks = 0, failed_picks = 0,
        accuracy_rate = 0.0, average_pick_time = 0.0, last_updated = datetime('now')
''')
conn.executemany('''
    INSERT OR IGNORE INTO inventory
    (sku, item_name, batch_code, quantity, location, expiry_date)
    VALUES (?, ?, ?, ?, ?, ?)
''', starter_inventory)
conn.commit()

counts = {}
for table in ('orders', 'verification_log', 'audit_trail', 'pick_alerts', 'inventory'):
    counts[table] = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
print(counts)
conn.close()
