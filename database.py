import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('kemsa_wms.db')
    cursor = conn.cursor()
    
    # Run the table setup from schema.sql
    with open('schema.sql', 'r') as f:
        cursor.executescript(f.read())
    
    # Insert sample staff members
    sample_staff = [
        ('Allan Kamau', 'sct221-0673/20223', 'Warehouse Operations', 'warehouse_staff'),
        ('Gloire Mugisha', 'sct221-0971/2021', 'Warehouse Operations', 'warehouse_staff'),
        ('Stacy Wangeci', 'sct221-0635/2023', 'Warehouse Operations', 'warehouse_staff'),
        ('MaryCynthia Gitau', 'sct221-0730/2023', 'Warehouse Operations', 'warehouse_staff'),
    ]
    
    cursor.executemany('''
        INSERT INTO staff (operator_name, employee_id, department, role)
        VALUES (?, ?, ?, ?)
    ''', sample_staff)
    
    # Insert sample inventory
    sample_inventory = [
        ('MED-101', 'Paracetamol 500mg', 'BATCH-2026A', 50, 'Shelf A1', '2026-12-31'),
        ('MED-204', 'Amoxicillin 250mg', 'BATCH-2025B', 75, 'Shelf B3', '2025-05-15'),
        ('MED-305', 'Ibuprofen 400mg', 'BATCH-2027C', 100, 'Shelf C2', '2027-08-20'),
        ('MED-402', 'Aspirin 100mg', 'BATCH-2026D', 60, 'Shelf D1', '2026-10-15'),
        ('MED-503', 'Vitamin C 500mg', 'BATCH-2027E', 120, 'Shelf E5', '2027-06-30'),
        ('MED-601', 'Surgical Gloves', 'BATCH-2027F', 200, 'Shelf F1', '2027-09-30'),
        ('MED-602', 'Sterile Syringes 5ml', 'BATCH-2027G', 150, 'Shelf F2', '2027-12-31'),
        ('MED-603', 'Gauze Swabs 10cm', 'BATCH-2028H', 300, 'Shelf G1', '2028-03-31'),
        ('MED-604', 'Hand Sanitizer 500ml', 'BATCH-2027I', 100, 'Shelf G2', '2027-07-31'),
    ]
    
    cursor.executemany('''
        INSERT INTO inventory (sku, item_name, batch_code, quantity, location, expiry_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', sample_inventory)
    
    # Initialize staff performance records
    for i in range(1, 5):
        cursor.execute('''
            INSERT INTO staff_performance (staff_id, total_picks, successful_picks, failed_picks, accuracy_rate)
            VALUES (?, 0, 0, 0, 0.0)
        ''', (i,))
    
    conn.commit()
    conn.close()
    print("✓ Database 'kemsa_wms.db' initialized successfully!")
    print("✓ Sample staff: 4 members")
    print("✓ Starter inventory: 10 items")
    print("✓ Sample orders: none (ready for user-created orders)")
    print("\nDatabase initialization complete!")

if __name__ == '__main__':
    init_db()