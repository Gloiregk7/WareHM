from flask import Flask, jsonify, request, render_template
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'kemsa_wms.db')

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# --- FRONTEND PAGES ---
@app.route('/')
@app.route('/orders')
def orders_page():
    return render_template('orders.html')

@app.route('/verify')
def verify_page():
    return render_template('verify.html')

@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

# --- REST API ENDPOINTS ---
@app.route('/api/orders', methods=['GET'])
def get_orders():
    conn = get_db_connection()
    orders = conn.execute("SELECT * FROM orders WHERE status = 'PENDING'").fetchall()
    conn.close()
    return jsonify([dict(order) for order in orders])

@app.route('/api/verify', methods=['POST'])
def verify_pick():
    data = request.json
    order_id = data.get('order_id')
    scanned_sku = data.get('sku')
    scanned_batch = data.get('batch_code')
    scanned_expiry = data.get('expiry_date')
    operator = data.get('operator', 'Operator 1')

    conn = get_db_connection()
    order = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()

    if not order:
        conn.close()
        return jsonify({"result": "REJECTED", "errors": ["INVALID_ORDER"]}), 404

    errors = []
    if scanned_sku != order['sku']:
        errors.append("SKU_MISMATCH")
    if scanned_batch != order['target_batch']:
        errors.append("BATCH_MISMATCH")
    
    today = datetime.now().strftime('%Y-%m-%d')
    if scanned_expiry < today:
        errors.append("EXPIRED_STOCK")

    result = "APPROVED" if not errors else "REJECTED"
    error_str = ",".join(errors) if errors else None

    conn.execute('''
        INSERT INTO verification_log (order_id, sku, scanned_batch, scanned_expiry, result, error_codes, operator)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (order_id, scanned_sku, scanned_batch, scanned_expiry, result, error_str, operator))

    if result == "APPROVED":
        conn.execute("UPDATE orders SET status = 'COMPLETED' WHERE order_id = ?", (order_id,))

    conn.commit()
    conn.close()

    return jsonify({"result": result, "errors": errors})

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_metrics():
    conn = get_db_connection()
    total_picks = conn.execute("SELECT COUNT(*) FROM verification_log").fetchone()[0]
    approved = conn.execute("SELECT COUNT(*) FROM verification_log WHERE result = 'APPROVED'").fetchone()[0]
    rejected = conn.execute("SELECT COUNT(*) FROM verification_log WHERE result = 'REJECTED'").fetchone()[0]
    logs = conn.execute("SELECT * FROM verification_log ORDER BY timestamp DESC LIMIT 10").fetchall()
    conn.close()

    return jsonify({
        "total_picks": total_picks,
        "approved": approved,
        "rejected": rejected,
        "recent_logs": [dict(log) for log in logs]
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)