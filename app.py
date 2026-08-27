from flask import Flask, jsonify, request, render_template
import os
import sqlite3
from datetime import datetime
import time

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'kemsa_wms.db')

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ==================== FRONTEND PAGES ====================

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

@app.route('/staff')
def staff_page():
    return render_template('staff_dashboard.html')

@app.route('/reports')
def reports_page():
    return render_template('reports.html')

# ==================== HEALTH CHECK ====================

@app.route('/api/health')
def health_check():
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        return jsonify({"status": "OK", "database": "connected"})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

# ==================== STAFF API ====================

@app.route('/api/staff', methods=['GET'])
def get_staff():
    try:
        conn = get_db_connection()
        staff = conn.execute(
            "SELECT staff_id, operator_name, employee_id, department, role, status FROM staff"
        ).fetchall()
        conn.close()
        return jsonify([dict(s) for s in staff])
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/api/staff', methods=['POST'])
def create_staff():
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO staff (operator_name, employee_id, department, role)
            VALUES (?, ?, ?, ?)
        ''', (data['operator_name'], data['employee_id'], data['department'], data.get('role', 'warehouse_staff')))
        conn.commit()
        staff_id = conn.lastrowid
        conn.close()
        return jsonify({"status": "SUCCESS", "staff_id": staff_id})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/api/staff/<int:staff_id>', methods=['GET'])
def get_staff_detail(staff_id):
    try:
        conn = get_db_connection()
        staff = conn.execute("SELECT * FROM staff WHERE staff_id = ?", (staff_id,)).fetchone()
        if not staff:
            return jsonify({"status": "ERROR", "message": "Staff not found"}), 404
        performance = conn.execute("SELECT * FROM staff_performance WHERE staff_id = ?", (staff_id,)).fetchone()
        conn.close()
        return jsonify({"staff": dict(staff), "performance": dict(performance) if performance else None})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

# ==================== ORDERS API ====================

@app.route('/api/orders', methods=['GET'])
def get_orders():
    try:
        status = request.args.get('status', 'PENDING')
        conn = get_db_connection()
        orders = conn.execute(
            "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC", (status,)
        ).fetchall()
        conn.close()
        return jsonify([dict(order) for order in orders])
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order_detail(order_id):
    try:
        conn = get_db_connection()
        order = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not order:
            return jsonify({"status": "ERROR", "message": "Order not found"}), 404
        alerts = conn.execute("SELECT * FROM pick_alerts WHERE order_id = ?", (order_id,)).fetchall()
        conn.close()
        return jsonify({"order": dict(order), "alerts": [dict(a) for a in alerts]})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

# ==================== VERIFICATION API ====================

@app.route('/api/verify', methods=['POST'])
def verify_pick():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "ERROR", "message": "Request body is required"}), 400

        conn = get_db_connection()
        
        # Get order details
        order = conn.execute("SELECT * FROM orders WHERE order_id = ?", (data['order_id'],)).fetchone()
        if not order:
            return jsonify({"status": "ERROR", "message": "Order not found"}), 404
        
        # Simulate verification logic
        errors = []
        result = "APPROVED"
        
        scanned_sku = data.get('sku')
        scanned_batch = data.get('batch', data.get('batch_code'))
        scanned_expiry = data.get('expiry', data.get('expiry_date'))

        if order['sku'] != scanned_sku:
            errors.append({"code": "SKU_MISMATCH", "message": "Scanned SKU does not match the order"})
            result = "REJECTED"
        
        if order['target_batch'] != scanned_batch:
            errors.append({"code": "BATCH_MISMATCH", "message": "Scanned batch does not match the order"})
            result = "REJECTED"
        
        if order['expiry_date'] != scanned_expiry:
            errors.append({"code": "EXPIRY_MISMATCH", "message": "Scanned expiry date does not match the order"})
            result = "REJECTED"
        
        # Log the verification
        conn.execute('''
            INSERT INTO verification_log (order_id, sku, scanned_batch, scanned_expiry, result, error_codes, operator_id, station_id, verification_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['order_id'],
            data.get('sku'),
            scanned_batch,
            scanned_expiry,
            result,
            ','.join(error["code"] for error in errors) if errors else None,
            data.get('operator_id', data.get('staff_id', 1)),
            data.get('station_id', 1),
            0.5
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "SUCCESS",
            "result": result,
            "errors": errors,
            "verification_time": 500
        })
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

# ==================== ALERTS API ====================

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    try:
        conn = get_db_connection()
        alerts = conn.execute("SELECT * FROM pick_alerts WHERE alert_status = 'ACTIVE' ORDER BY created_at DESC LIMIT 50").fetchall()
        conn.close()
        return jsonify({"alerts": [dict(a) for a in alerts]})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

# ==================== DASHBOARD API ====================

@app.route('/api/dashboard')
def dashboard_data():
    try:
        conn = get_db_connection()
        
        # Get metrics
        stats = conn.execute('''
            SELECT 
                COUNT(*) as total_picks,
                SUM(CASE WHEN result = 'APPROVED' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN result = 'REJECTED' THEN 1 ELSE 0 END) as rejected,
                ROUND(100.0 * SUM(CASE WHEN result = 'APPROVED' THEN 1 ELSE 0 END) / COUNT(*), 1) as accuracy
            FROM verification_log
        ''').fetchone()
        
        # Get recent logs
        recent_logs = conn.execute('''
            SELECT * FROM verification_log ORDER BY timestamp DESC LIMIT 10
        ''').fetchall()
        
        # Get order status
        orders = conn.execute('''
            SELECT status, COUNT(*) as count FROM orders GROUP BY status
        ''').fetchall()
        
        # Get alerts
        alerts = conn.execute('''
            SELECT severity, COUNT(*) as count FROM pick_alerts 
            WHERE alert_status = 'ACTIVE' GROUP BY severity
        ''').fetchall()
        
        conn.close()
        
        stats_data = dict(stats) if stats else {}
        total_picks = stats_data.get("total_picks") or 0
        approved = stats_data.get("approved") or 0
        rejected = stats_data.get("rejected") or 0
        accuracy = stats_data.get("accuracy") or 0
        order_counts = {dict(o)['status']: dict(o)['count'] for o in orders}

        return jsonify({
            "stats": stats_data,
            "total_picks": total_picks,
            "approved": approved,
            "rejected": rejected,
            "accuracy_rate": accuracy,
            "pending_orders": order_counts.get("PENDING", 0),
            "completed_orders": order_counts.get("COMPLETED", 0),
            "recent_logs": [dict(log) for log in recent_logs],
            "orders": order_counts,
            "alerts": {dict(a)['severity']: dict(a)['count'] for a in alerts}
        })
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

# ==================== REPORTS API ====================

@app.route('/api/reports/accuracy')
def accuracy_report():
    try:
        conn = get_db_connection()
        report = conn.execute('''
            SELECT 
                COUNT(*) as total_picks,
                SUM(CASE WHEN result = 'APPROVED' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN result = 'REJECTED' THEN 1 ELSE 0 END) as rejected,
                ROUND(100.0 * SUM(CASE WHEN result = 'APPROVED' THEN 1 ELSE 0 END) / COUNT(*), 2) as accuracy_percentage
            FROM verification_log
        ''').fetchone()
        conn.close()
        return jsonify(dict(report) if report else {})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
