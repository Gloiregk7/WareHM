from flask import Flask, jsonify, request, render_template
import os
import sqlite3
from datetime import datetime
import time

# Import custom modules
from vision_system import VisionSystem
from middleware import Middleware
from alerts import AlertSystem
from audit_system import AuditSystem
from reports import ReportingSystem

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'kemsa_wms.db')

# Initialize systems
vision_system = VisionSystem()
middleware = Middleware()
alert_system = AlertSystem(DB_NAME)
audit_system = AuditSystem(DB_NAME)
reporting_system = ReportingSystem(DB_NAME)

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

#  FRONTEND PAGES 

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

# STAFF & USER MANAGEMENT 

@app.route('/api/staff', methods=['GET'])
def get_staff():
    """Get all staff members"""
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
    """Register new staff member"""
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
        
        return jsonify({"status": "SUCCESS", "staff_id": staff_id, "message": "Staff member registered"})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/api/staff/<int:staff_id>', methods=['GET'])
def get_staff_detail(staff_id):
    """Get staff details and performance"""
    try:
        conn = get_db_connection()
        staff = conn.execute(
            "SELECT * FROM staff WHERE staff_id = ?", (staff_id,)
        ).fetchone()
        
        if not staff:
            conn.close()
            return jsonify({"status": "ERROR", "message": "Staff not found"}), 404
        
        performance = conn.execute(
            "SELECT * FROM staff_performance WHERE staff_id = ?", (staff_id,)
        ).fetchone()
        
        conn.close()
        
        return jsonify({
            "staff": dict(staff),
            "performance": dict(performance) if performance else None
        })
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

#  ORDER MANAGEMENT 

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Get pending orders"""
    status = request.args.get('status', 'PENDING')
    try:
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
    """Get order details"""
    try:
        conn = get_db_connection()
        order = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        
        if not order:
            conn.close()
            return jsonify({"status": "ERROR", "message": "Order not found"}), 404
        
        alerts = conn.execute(
            "SELECT * FROM pick_alerts WHERE order_id = ? ORDER BY created_at DESC", (order_id,)
        ).fetchall()
        
        conn.close()
        
        return jsonify({
            "order": dict(order),
            "alerts": [dict(a) for a in alerts]
        })
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create new order"""
    try:
        data = request.json
        conn = get_db_connection()
        
        conn.execute('''
            INSERT INTO orders (sku, item_name, target_batch, required_quantity, expiry_date, location, destination)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['sku'], data['item_name'], data['target_batch'], data.get('required_quantity', 1),
              data['expiry_date'], data['location'], data['destination']))
        
        conn.commit()
        order_id = conn.lastrowid
        conn.close()
        
        return jsonify({"status": "SUCCESS", "order_id": order_id, "message": "Order created"})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

# Vision and verification system

@app.route('/api/verify', methods=['POST'])
def verify_pick():
    """
    Main verification endpoint
    Processes vision system input and verifies against order
    """
    try:
        data = request.json
        order_id = data.get('order_id')
        staff_id = data.get('staff_id', 1)
        station_id = data.get('station_id', 'STATION-01')
        image_source = data.get('image_source', 0)
        
        # Get order
        conn = get_db_connection()
        order = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        conn.close()
        
        if not order:
            return jsonify({"status": "ERROR", "message": "Order not found"}), 404
        
        # Process image
        image_result = vision_system.capture_and_process_image(image_source)
        
        if image_result["status"] == "ERROR":
            return jsonify(image_result), 500
        
        # Verify pick
        order_data = {
            'sku': order['sku'],
            'target_batch': order['target_batch'],
            'expiry_date': order['expiry_date']
        }
        
        verification_result = vision_system.verify_pick(image_result, order_data)
        
        # Get error codes
        error_codes = ",".join([e['code'] for e in verification_result['errors']]) if verification_result['errors'] else None
        
        # Log transaction
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO verification_log 
            (order_id, sku, scanned_batch, scanned_expiry, result, error_codes, operator_id, station_id, verification_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (order_id, order['sku'], 
              verification_result['scanned_data'].get('batch'),
              verification_result['scanned_data'].get('expiry'),
              verification_result['status'], error_codes, staff_id, station_id, 
              verification_result['verification_time']))
        
        if verification_result['status'] == "APPROVED":
            conn.execute("UPDATE orders SET status = 'COMPLETED' WHERE order_id = ?", (order_id,))
        else:
            # Create alerts for each error
            for error in verification_result['errors']:
                alert_system.create_alert(
                    order_id, 
                    error['code'], 
                    error['code'],
                    error['message'],
                    error['severity']
                )
        
        conn.commit()
        conn.close()
        
        # Log to audit trail
        audit_system.log_picking_transaction(
            staff_id, order_id, order['sku'],
            verification_result['scanned_data'].get('batch'),
            verification_result['scanned_data'].get('expiry'),
            verification_result['status'], error_codes, station_id,
            verification_result['verification_time']
        )
        
        # Trigger alerts
        alert_data = None
        if verification_result['status'] == "REJECTED":
            alert_data = alert_system.trigger_visual_alert(
                error_codes.split(',')[0] if error_codes else 'PICKING_ERROR',
                verification_result['errors'][0]['message'] if verification_result['errors'] else 'Unknown error'
            )
        
        return jsonify({
            "result": verification_result['status'],
            "errors": verification_result['errors'],
            "verification_time": verification_result['verification_time'],
            "alert": alert_data
        })
        
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/api/verify/batch', methods=['POST'])
def verify_batch():
    """Verify multiple picks in batch"""
    try:
        data = request.json
        picks = data.get('picks', [])
        staff_id = data.get('staff_id', 1)
        
        results = []
        for pick in picks:
            pick['staff_id'] = staff_id
            # Call individual verify for each pick
            result = verify_pick()
            results.append(result.json)
        
        return jsonify({
            "status": "SUCCESS",
            "batch_size": len(picks),
            "results": results
        })
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

# Alert management

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get all active alerts"""
    limit = request.args.get('limit', 50, type=int)
    alerts = alert_system.get_active_alerts(limit)
    return jsonify({"alerts": alerts})

@app.route('/api/alerts/<int:order_id>', methods=['GET'])
def get_order_alerts(order_id):
    """Get alerts for specific order"""
    alerts = alert_system.get_alerts_by_order(order_id)
    return jsonify({"alerts": alerts, "order_id": order_id})

@app.route('/api/alerts/<int:alert_id>/resolve', methods=['PUT'])
def resolve_alert(alert_id):
    """Resolve an alert"""
    result = alert_system.resolve_alert(alert_id)
    return jsonify(result)

@app.route('/api/alerts/statistics', methods=['GET'])
def get_alert_stats():
    """Get alert statistics"""
    stats = alert_system.get_alert_statistics()
    return jsonify(stats)

# Audit and tracking

@app.route('/api/audit', methods=['GET'])
def get_audit_trail():
    """Get audit trail"""
    order_id = request.args.get('order_id', type=int)
    staff_id = request.args.get('staff_id', type=int)
    action = request.args.get('action')
    limit = request.args.get('limit', 100, type=int)
    
    records = audit_system.get_audit_trail(order_id, staff_id, action, limit)
    return jsonify({"audit_records": records})

@app.route('/api/audit/order/<int:order_id>', methods=['GET'])
def get_order_history(order_id):
    """Get complete picking history for order"""
    history = audit_system.get_picking_history(order_id)
    return jsonify(history)

@app.route('/api/audit/staff/<int:staff_id>', methods=['GET'])
def get_staff_history(staff_id):
    """Get staff audit history"""
    days = request.args.get('days', 30, type=int)
    history = audit_system.get_staff_audit_history(staff_id, days)
    return jsonify(history)

@app.route('/api/compliance-report', methods=['GET'])
def get_compliance_report():
    """Generate compliance report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    report = audit_system.generate_compliance_report(start_date, end_date)
    return jsonify(report)

# Reporting and analytics

@app.route('/api/reports/accuracy', methods=['GET'])
def get_accuracy_report():
    """Get picking accuracy report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    report = reporting_system.get_picking_accuracy_report(start_date, end_date)
    return jsonify(report)

@app.route('/api/reports/staff-performance', methods=['GET'])
def get_staff_performance():
    """Get staff performance report"""
    staff_id = request.args.get('staff_id', type=int)
    report = reporting_system.get_staff_performance_report(staff_id)
    return jsonify(report)

@app.route('/api/reports/inventory', methods=['GET'])
def get_inventory_report():
    """Get inventory verification report"""
    report = reporting_system.get_inventory_verification_report()
    return jsonify(report)

@app.route('/api/reports/error-trends', methods=['GET'])
def get_error_trends():
    """Get error trend report"""
    days = request.args.get('days', 30, type=int)
    report = reporting_system.get_error_trend_report(days)
    return jsonify(report)

@app.route('/api/reports/dashboard', methods=['GET'])
def get_compliance_dashboard():
    """Get comprehensive compliance dashboard data"""
    data = reporting_system.get_compliance_dashboard_data()
    return jsonify(data)

# Dashboard and metrics

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_metrics():
    """Get main dashboard metrics"""
    try:
        conn = get_db_connection()
        
        total_picks = conn.execute("SELECT COUNT(*) FROM verification_log").fetchone()[0]
        approved = conn.execute("SELECT COUNT(*) FROM verification_log WHERE result = 'APPROVED'").fetchone()[0]
        rejected = conn.execute("SELECT COUNT(*) FROM verification_log WHERE result = 'REJECTED'").fetchone()[0]
        active_alerts = conn.execute("SELECT COUNT(*) FROM pick_alerts WHERE alert_status = 'ACTIVE'").fetchone()[0]
        
        pending_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'PENDING'").fetchone()[0]
        completed_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'COMPLETED'").fetchone()[0]
        
        logs = conn.execute(
            "SELECT * FROM verification_log ORDER BY timestamp DESC LIMIT 10"
        ).fetchall()
        
        conn.close()
        
        accuracy = round(100 * approved / total_picks, 2) if total_picks > 0 else 0
        
        return jsonify({
            "total_picks": total_picks,
            "approved": approved,
            "rejected": rejected,
            "accuracy_rate": accuracy,
            "active_alerts": active_alerts,
            "pending_orders": pending_orders,
            "completed_orders": completed_orders,
            "recent_logs": [dict(log) for log in logs]
        })
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

# Middleware and system

@app.route('/api/middleware/devices', methods=['POST'])
def register_device():
    """Register hardware device"""
    data = request.json
    result = middleware.register_device(data['device_id'], data['device_type'], data['endpoint'])
    return jsonify(result)

@app.route('/api/middleware/status', methods=['GET'])
def get_system_status():
    """Get system status"""
    status = middleware.get_system_status()
    return jsonify(status)

@app.route('/api/middleware/health', methods=['GET'])
def check_device_health():
    """Check device health"""
    health = middleware.check_device_health()
    return jsonify(health)

@app.route('/api/middleware/heartbeat/<device_id>', methods=['POST'])
def device_heartbeat(device_id):
    """Receive device heartbeat"""
    result = middleware.handle_device_heartbeat(device_id)
    return jsonify(result)

# Error handlers

@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "ERROR", "message": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"status": "ERROR", "message": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
