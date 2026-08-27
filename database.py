import sqlite3

def init_db():
    conn = sqlite3.connect('kemsa_wms.db')
    cursor = conn.cursor()
    
    # Run the table setup from schema.sql
    with open('schema.sql', 'r') as f:
        cursor.executescript(f.read())
        
    # Insert sample test orders
    sample_orders = [
        ('MED-101', 'Paracetamol 500mg', 'BATCH-2026A', '2026-12-31', 'Shelf A1', 'Nairobi West Hospital', 'PENDING'),
        ('MED-204', 'Amoxicillin 250mg', 'BATCH-2025B', '2025-05-15', 'Shelf B3', 'Kenyatta National Hospital', 'PENDING'),
        ('MED-305', 'Ibuprofen 400mg', 'BATCH-2027C', '2027-08-20', 'Shelf C2', 'Mbagathi Hospital', 'PENDING')
    ]
    
    cursor.executemany('''
        INSERT INTO orders (sku, item_name, target_batch, expiry_date, location, destination, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', sample_orders)
    
    conn.commit()
    conn.close()
    print("Database 'kemsa_wms.db' initialized with sample orders!")

if __name__ == '__main__':
    init_db()