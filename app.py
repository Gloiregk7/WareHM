from flask import Flask, jsonify, request, render_template, session, redirect, url_for
import os
import sqlite3
from datetime import datetime
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('KEMSA_SECRET_KEY', 'development-only-change-me')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'kemsa_wms.db')

def ensure_order_columns():
    conn = sqlite3.connect(DB_NAME)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)")}
    if 'dispatcher_name' not in columns:
        conn.execute("ALTER TABLE orders ADD COLUMN dispatcher_name TEXT NOT NULL DEFAULT ''")
        conn.commit()
    conn.close()

ensure_order_columns()

PUBLIC_ENDPOINTS = {'login', 'static'}

@app.before_request
def require_staff_login():
    if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
        return None
    if session.get('staff_id'):
        return None
    if request.path.startswith('/api/'):
        return jsonify({
            "status": "UNAUTHORIZED",
            "message": "Please sign in with your staff name and staff ID"
        }), 401
    return redirect(url_for('login', next=request.full_path))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json(silent=True) if request.is_json else request.form
        operator_name = str(data.get('operator_name', '')).strip()
        staff_id = str(data.get('staff_id', '')).strip()
        next_url = data.get('next') or request.args.get('next') or url_for('orders_page')

        try:
            conn = get_db_connection()
            staff = conn.execute('''
                SELECT staff_id, operator_name, employee_id, department, role
                FROM staff
                                WHERE employee_id = ? AND status = 'ACTIVE'
                  AND lower(trim(operator_name)) = lower(trim(?))
                        ''', (staff_id.zfill(4), operator_name)).fetchone()
            conn.close()
        except Exception as e:
            if request.is_json:
                return jsonify({"status": "ERROR", "message": str(e)}), 500
            return render_template('login.html', error='Unable to verify staff details.'), 500

        if not staff:
            message = 'Staff name or Staff ID is incorrect. Please use your registered details.'
            if request.is_json:
                return jsonify({"status": "ERROR", "message": message}), 401
            return render_template('login.html', error=message, next=next_url), 401

        session.clear()
        session['staff_id'] = staff['staff_id']
        session['operator_name'] = staff['operator_name']
        session['employee_id'] = staff['employee_id']
        if request.is_json:
            return jsonify({"status": "SUCCESS", "staff": dict(staff)})
        return redirect(next_url if next_url.startswith('/') else url_for('orders_page'))

    if session.get('staff_id'):
        return redirect(url_for('orders_page'))
    return render_template('login.html', next=request.args.get('next', ''))

@app.post('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

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

@app.route('/inventory')
def inventory_page():
    return render_template('inventory.html')

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

@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    try:
        conn = get_db_connection()
        items = conn.execute(
            "SELECT * FROM inventory ORDER BY item_name, batch_code"
        ).fetchall()
        conn.close()
        return jsonify([dict(item) for item in items])
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/api/inventory', methods=['POST'])
def create_inventory_item():
    data = request.get_json(silent=True) or {}
    required_fields = ('sku', 'item_name', 'batch_code', 'quantity', 'location', 'expiry_date')
    missing_fields = [field for field in required_fields if data.get(field) in (None, '')]
    if missing_fields:
        return jsonify({
            "status": "ERROR",
            "message": "Missing required fields: " + ", ".join(missing_fields)
        }), 400

    try:
        quantity = int(data['quantity'])
        if quantity < 0:
            raise ValueError
        datetime.strptime(data['expiry_date'], '%Y-%m-%d')
    except (TypeError, ValueError):
        return jsonify({
            "status": "ERROR",
            "message": "Quantity must be a non-negative integer and expiry_date must use YYYY-MM-DD"
        }), 400

    try:
        conn = get_db_connection()
        cursor = conn.execute('''
            INSERT INTO inventory (sku, item_name, batch_code, quantity, location, expiry_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            str(data['sku']).strip(),
            str(data['item_name']).strip(),
            str(data['batch_code']).strip(),
            quantity,
            str(data['location']).strip(),
            data['expiry_date']
        ))
        conn.commit()
        item = conn.execute(
            "SELECT * FROM inventory WHERE inventory_id = ?", (cursor.lastrowid,)
        ).fetchone()
        conn.close()
        return jsonify({"status": "SUCCESS", "item": dict(item)}), 201
    except sqlite3.IntegrityError:
        return jsonify({"status": "ERROR", "message": "SKU already exists"}), 409
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    try:
        status = request.args.get('status', 'ALL')
        conn = get_db_connection()
        order_columns = '''order_id, sku, item_name, target_batch, required_quantity,
                           expiry_date, location, destination, status, assigned_to, created_at'''
        if status == 'ALL':
            orders = conn.execute(f"SELECT {order_columns} FROM orders ORDER BY order_id ASC").fetchall()
        else:
            orders = conn.execute(
                f"SELECT {order_columns} FROM orders WHERE status = ? ORDER BY order_id ASC", (status,)
            ).fetchall()
        conn.close()
        return jsonify([
            {**dict(order), "status_label": order['status'].replace('_', ' ').title()}
            for order in orders
        ])
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json(silent=True) or {}
    required_fields = ('sku', 'item_name', 'target_batch', 'required_quantity', 'expiry_date', 'location', 'destination', 'dispatcher_name')
    missing_fields = [field for field in required_fields if data.get(field) in (None, '')]
    if missing_fields:
        return jsonify({
            "status": "ERROR",
            "message": "Missing required fields: " + ", ".join(missing_fields)
        }), 400

    try:
        quantity = int(data['required_quantity'])
        if quantity <= 0:
            raise ValueError
        datetime.strptime(data['expiry_date'], '%Y-%m-%d')
    except (TypeError, ValueError):
        return jsonify({
            "status": "ERROR",
            "message": "required_quantity must be positive and expiry_date must use YYYY-MM-DD"
        }), 400

    try:
        conn = get_db_connection()
        inventory = conn.execute(
            "SELECT item_name, quantity FROM inventory WHERE sku = ? AND batch_code = ? AND expiry_date = ?",
            (data['sku'].strip(), data['target_batch'].strip(), data['expiry_date'])
        ).fetchone()
        if not inventory:
            possible_sku = conn.execute(
                "SELECT sku FROM inventory WHERE lower(sku) = lower(?) LIMIT 1",
                (data['sku'].strip(),)
            ).fetchone()
            conn.close()
            if possible_sku:
                return jsonify({
                    "status": "ERROR",
                    "message": "The batch code or expiry date does not match the selected SKU"
                }), 404
            return jsonify({
                "status": "ERROR",
                "message": "SKU not recognized. Please verify the SKU spelling against Inventory"
            }), 404
        if inventory['item_name'].strip().casefold() != str(data['item_name']).strip().casefold():
            conn.close()
            return jsonify({
                "status": "ERROR",
                "message": "Item name does not match the selected inventory record"
            }), 422
        if inventory['quantity'] < quantity:
            conn.close()
            return jsonify({"status": "ERROR", "message": "Insufficient inventory quantity"}), 409

        cursor = conn.execute('''
            INSERT INTO orders (sku, item_name, target_batch, required_quantity, expiry_date, location, destination, dispatcher_name, assigned_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['sku'].strip(), inventory['item_name'], data['target_batch'].strip(), quantity,
            data['expiry_date'], data['location'].strip(), data['destination'].strip(),
            data['dispatcher_name'].strip(), session['staff_id']
        ))
        conn.commit()
        order = conn.execute("SELECT * FROM orders WHERE order_id = ?", (cursor.lastrowid,)).fetchone()
        conn.close()
        return jsonify({"status": "SUCCESS", "order": dict(order)}), 201
    except sqlite3.IntegrityError as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    try:
        conn = get_db_connection()
        order = conn.execute(
            "SELECT status FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone()
        if not order:
            conn.close()
            return jsonify({"status": "ERROR", "message": "Order record was not found"}), 404
        if order['status'] != 'PENDING':
            conn.close()
            return jsonify({
                "status": "ERROR",
                "message": "Verified orders cannot be deleted"
            }), 409
        verification = conn.execute(
            "SELECT 1 FROM verification_log WHERE order_id = ? LIMIT 1", (order_id,)
        ).fetchone()
        if verification:
            conn.close()
            return jsonify({
                "status": "ERROR",
                "message": "This order has a verification record and cannot be deleted"
            }), 409
        conn.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "SUCCESS", "message": "Order deleted successfully"})
    except sqlite3.IntegrityError:
        return jsonify({"status": "ERROR", "message": "Order cannot be deleted because audit records reference it"}), 409
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order_detail(order_id):
    try:
        conn = get_db_connection()
        order = conn.execute('''
            SELECT order_id, sku, item_name, target_batch, required_quantity,
                   expiry_date, location, destination, status, assigned_to, created_at
            FROM orders WHERE order_id = ?
        ''', (order_id,)).fetchone()
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
            session['staff_id'],
            data.get('station_id', 1),
            0.5
        ))

        dispatch_status = None
        remaining_quantity = None
        if result == "APPROVED" and order['status'] == 'PENDING':
            inventory = conn.execute(
                "SELECT inventory_id, quantity FROM inventory WHERE sku = ? AND batch_code = ?",
                (order['sku'], order['target_batch'])
            ).fetchone()
            if not inventory or inventory['quantity'] < order['required_quantity']:
                conn.rollback()
                return jsonify({"status": "ERROR", "message": "Insufficient matching inventory for this order"}), 409

            remaining_quantity = inventory['quantity'] - order['required_quantity']
            conn.execute(
                "UPDATE inventory SET quantity = ?, updated_at = datetime('now') WHERE inventory_id = ?",
                (remaining_quantity, inventory['inventory_id'])
            )
            conn.execute(
                "UPDATE orders SET status = 'READY_FOR_DISPATCH' WHERE order_id = ?",
                (order['order_id'],)
            )
            dispatch_status = 'READY_FOR_DISPATCH'
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "SUCCESS",
            "result": result,
            "errors": errors,
            "verification_time": 500,
            "order_status": dispatch_status or order['status'],
            "order_status_label": (dispatch_status or order['status']).replace('_', ' ').title(),
            "remaining_inventory": remaining_quantity
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
            SELECT vl.*, o.item_name, o.required_quantity, o.destination, o.location, o.status AS order_status,
                   i.quantity AS remaining_inventory
            FROM verification_log vl
            JOIN orders o ON o.order_id = vl.order_id
            LEFT JOIN inventory i ON i.sku = o.sku AND i.batch_code = o.target_batch
            ORDER BY vl.timestamp DESC LIMIT 10
        ''').fetchall()

        dispatch_orders = conn.execute('''
                 SELECT o.order_id, o.sku, o.item_name, o.required_quantity, o.target_batch,
                     o.destination, o.location, o.dispatcher_name, o.status, o.created_at,
                   i.quantity AS remaining_inventory
            FROM orders o
            LEFT JOIN inventory i ON i.sku = o.sku AND i.batch_code = o.target_batch
            ORDER BY o.order_id DESC LIMIT 20
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
            "completed_orders": order_counts.get("COMPLETED", 0) + order_counts.get("READY_FOR_DISPATCH", 0),
            "recent_logs": [dict(log) for log in recent_logs],
            "dispatch_orders": [
                {**dict(order), "status_label": order['status'].replace('_', ' ').title()}
                for order in dispatch_orders
            ],
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
