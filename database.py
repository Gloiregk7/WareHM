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
        ('John Kamau', 'EMP-001', 'Warehouse Operations', 'warehouse_staff'),
        ('Grace Wanjiru', 'EMP-002', 'Warehouse Operations', 'warehouse_staff'),
        ('Peter Mwangi', 'EMP-003', 'Quality Assurance', 'supervisor'),
        ('Mary Kipchoge', 'EMP-004', 'Warehouse Operations', 'warehouse_staff'),
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
    ]
    
    cursor.executemany('''
        INSERT INTO inventory (sku, item_name, batch_code, quantity, location, expiry_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', sample_inventory)
    
    # Insert sample test orders
    sample_orders = [
        ('MED-101', 'Paracetamol 500mg', 'BATCH-2026A', 1, '2026-12-31', 'Shelf A1', 'Nairobi West Hospital', 'PENDING', 1),
        ('MED-204', 'Amoxicillin 250mg', 'BATCH-2025B', 2, '2025-05-15', 'Shelf B3', 'Kenyatta National Hospital', 'PENDING', 2),
        ('MED-305', 'Ibuprofen 400mg', 'BATCH-2027C', 3, '2027-08-20', 'Shelf C2', 'Mbagathi Hospital', 'PENDING', 1),
        ('MED-402', 'Aspirin 100mg', 'BATCH-2026D', 5, '2026-10-15', 'Shelf D1', 'Karen Hospital', 'PENDING', 3),
    ]
    
    cursor.executemany('''
        INSERT INTO orders (sku, item_name, target_batch, required_quantity, expiry_date, location, destination, status, assigned_to)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_orders)
    
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
    print("✓ Sample inventory: 5 items")
    print("✓ Sample orders: 4 pending")
    print("\nDatabase initialization complete!")

if __name__ == '__main__':
    init_db()