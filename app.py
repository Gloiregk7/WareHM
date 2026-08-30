from flask import Flask, jsonify, request, render_template, session, redirect, url_for
import os
import sqlite3
from datetime import datetime
import time
from werkzeug.security import check_password_hash, generate_password_hash
from reports import ReportingSystem
from audit_system import AuditSystem

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('KEMSA_SECRET_KEY', 'development-only-change-me')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'kemsa_wms.db')

def ensure_order_columns():
    conn = sqlite3.connect(DB_NAME)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS hospitals (
            hospital_id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_name TEXT NOT NULL,
            hospital_code TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS supervisors (
            supervisor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            supervisor_name TEXT NOT NULL,
            supervisor_code TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    ''')
    columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)")}
    if 'dispatcher_name' not in columns:
        conn.execute("ALTER TABLE orders ADD COLUMN dispatcher_name TEXT NOT NULL DEFAULT ''")
    if 'hospital_id' not in columns:
        conn.execute("ALTER TABLE orders ADD COLUMN hospital_id INTEGER")
    if not conn.execute("SELECT 1 FROM hospitals LIMIT 1").fetchone():
        conn.execute(
            "INSERT INTO hospitals (hospital_name, hospital_code, password_hash) VALUES (?, ?, ?)",
            ('Kenyatta National Hospital', 'KNH-001', generate_password_hash('hospital123'))
        )
    if not conn.execute("SELECT 1 FROM supervisors LIMIT 1").fetchone():
        conn.execute(
            "INSERT INTO supervisors (supervisor_name, supervisor_code, password_hash) VALUES (?, ?, ?)",
            ('Warehouse Supervisor', 'SUP-001', generate_password_hash('supervisor123'))
        )
    conn.commit()
    conn.close()

ensure_order_columns()

PUBLIC_ENDPOINTS = {'login', 'static'}

@app.before_request
def require_staff_login():
    if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
        return None
    if session.get('staff_id') or session.get('hospital_id') or session.get('supervisor_id'):
        if session.get('hospital_id') and request.endpoint not in {'hospital_orders_page', 'get_orders', 'create_order', 'delete_order', 'logout'}:
            if request.path.startswith('/api/'):
                return jsonify({"status": "FORBIDDEN", "message": "This area is for warehouse staff only"}), 403
            return redirect(url_for('hospital_orders_page'))
        if session.get('staff_id') and request.endpoint in {'dashboard_page', 'dashboard_data'}:
            if request.path.startswith('/api/'):
                return jsonify({"status": "FORBIDDEN", "message": "The supervisor dashboard is restricted to supervisors"}), 403
            return redirect(url_for('orders_page'))
        if session.get('staff_id') and request.endpoint in {'reports_page', 'accuracy_report'}:
            if request.path.startswith('/api/'):
                return jsonify({"status": "FORBIDDEN", "message": "Reports are restricted to supervisors"}), 403
            return redirect(url_for('orders_page'))
        return None
    if request.path.startswith('/api/'):
        return jsonify({
            "status": "UNAUTHORIZED",
            "message": "Please sign in with your staff name and staff ID"
        }), 401
    return redirect(url_for('login', next=request.full_path))

@app.after_request
def prevent_stale_data(response):
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json(silent=True) if request.is_json else request.form
        account_type = str(data.get('account_type', 'hospital')).strip().lower()
        next_url = data.get('next') or request.args.get('next')

        if account_type == 'hospital':
            hospital_code = str(data.get('hospital_code', '')).strip()
            password = str(data.get('password', ''))
            conn = get_db_connection()
            hospital = conn.execute('''
                SELECT hospital_id, hospital_name, hospital_code, password_hash
                FROM hospitals WHERE hospital_code = ? AND status = 'ACTIVE'
            ''', (hospital_code,)).fetchone()
            conn.close()
            if not hospital or not check_password_hash(hospital['password_hash'], password):
                message = 'Hospital code or password is incorrect.'
                if request.is_json:
                    return jsonify({"status": "ERROR", "message": message}), 401
                return render_template('login.html', error=message, next=next_url or '', account_type='hospital'), 401

            session.clear()
            session['hospital_id'] = hospital['hospital_id']
            session['hospital_name'] = hospital['hospital_name']
            session['hospital_code'] = hospital['hospital_code']
            destination = next_url if next_url and next_url.startswith('/') else url_for('hospital_orders_page')
            if request.is_json:
                return jsonify({"status": "SUCCESS", "hospital": dict(hospital)})
            return redirect(destination)

        if account_type == 'supervisor':
            supervisor_code = str(data.get('supervisor_code', '')).strip()
            password = str(data.get('password', ''))
            conn = get_db_connection()
            supervisor = conn.execute('''
                SELECT supervisor_id, supervisor_name, supervisor_code, password_hash
                FROM supervisors WHERE supervisor_code = ? AND status = 'ACTIVE'
            ''', (supervisor_code,)).fetchone()
            conn.close()
            if not supervisor or not check_password_hash(supervisor['password_hash'], password):
                message = 'Supervisor code or password is incorrect.'
                if request.is_json:
                    return jsonify({"status": "ERROR", "message": message}), 401
                return render_template('login.html', error=message, next=next_url or '', account_type='supervisor'), 401

            session.clear()
            session['supervisor_id'] = supervisor['supervisor_id']
            session['supervisor_name'] = supervisor['supervisor_name']
            session['supervisor_code'] = supervisor['supervisor_code']
            destination = next_url if next_url and next_url.startswith('/') else url_for('dashboard_page')
            if request.is_json:
                return jsonify({"status": "SUCCESS", "supervisor": dict(supervisor)})
            return redirect(destination)

        operator_name = str(data.get('operator_name', '')).strip()
        staff_id = str(data.get('staff_id', '')).strip()
        next_url = next_url or url_for('orders_page')

        try:
            conn = get_db_connection()
            staff = conn.execute('''
                SELECT staff_id, operator_name, employee_id, department, role
                FROM staff
                                WHERE employee_id = ? AND status = 'ACTIVE' AND role != 'supervisor'
                  AND lower(trim(operator_name)) = lower(trim(?))
                        ''', (staff_id, operator_name)).fetchone()
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
    if session.get('supervisor_id'):
        return redirect(url_for('dashboard_page'))
    if session.get('hospital_id'):
        return redirect(url_for('hospital_orders_page'))
    return render_template('login.html', next=request.args.get('next', ''), account_type='hospital')

@app.post('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

#  FRONTEND PAGES 

@app.route('/')
@app.route('/orders')
def orders_page():
    return render_template('orders.html')

@app.route('/hospital/orders')
def hospital_orders_page():
    return render_template('hospital_orders.html')

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

#  HEALTH CHECK 

@app.route('/api/health')
def health_check():
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        return jsonify({"status": "OK", "database": "connected"})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

# STAFF API 

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

# ORDERS API

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
        order_columns = '''o.order_id, o.sku, o.item_name, o.target_batch, o.required_quantity,
                           o.expiry_date, o.location, o.destination, o.status, o.assigned_to,
                           o.hospital_id, h.hospital_name, o.created_at'''
        order_filter = ''
        parameters = ()
        if session.get('hospital_id'):
            order_filter = ' AND o.hospital_id = ?'
            parameters = (session['hospital_id'],)
        if status == 'ALL':
            orders = conn.execute(f"SELECT {order_columns} FROM orders o LEFT JOIN hospitals h ON h.hospital_id = o.hospital_id WHERE 1=1 {order_filter} ORDER BY o.order_id ASC", parameters).fetchall()
        else:
            orders = conn.execute(
                f"SELECT {order_columns} FROM orders o LEFT JOIN hospitals h ON h.hospital_id = o.hospital_id WHERE o.status = ? {order_filter} ORDER BY o.order_id ASC", (status,) + parameters
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
    is_hospital_order = bool(session.get('hospital_id'))
    required_fields = ('sku', 'item_name', 'required_quantity') if is_hospital_order else ('sku', 'item_name', 'target_batch', 'required_quantity', 'expiry_date', 'location', 'destination', 'dispatcher_name')
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
        if not is_hospital_order:
            datetime.strptime(data['expiry_date'], '%Y-%m-%d')
    except (TypeError, ValueError):
        return jsonify({
            "status": "ERROR",
            "message": "required_quantity must be positive and expiry_date must use YYYY-MM-DD"
        }), 400

    try:
        conn = get_db_connection()
        if is_hospital_order:
            inventory = conn.execute(
                "SELECT item_name, batch_code, quantity, location, expiry_date FROM inventory WHERE sku = ?",
                (data['sku'].strip(),)
            ).fetchone()
        else:
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
            INSERT INTO orders (sku, item_name, target_batch, required_quantity, expiry_date, location, destination, dispatcher_name, assigned_to, hospital_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['sku'].strip(), inventory['item_name'], inventory['batch_code'] if is_hospital_order else data['target_batch'].strip(), quantity,
            inventory['expiry_date'] if is_hospital_order else data['expiry_date'], inventory['location'] if is_hospital_order else data['location'].strip(),
            session.get('hospital_name') if is_hospital_order else data['destination'].strip(),
            'Hospital Request' if is_hospital_order else data['dispatcher_name'].strip(),
            session.get('staff_id'), session.get('hospital_id')
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
            "SELECT status, hospital_id FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone()
        if not order:
            conn.close()
            return jsonify({"status": "ERROR", "message": "Order record was not found"}), 404
        if session.get('hospital_id') and order['hospital_id'] != session['hospital_id']:
            conn.close()
            return jsonify({
                "status": "ERROR",
                "message": "You can only manage orders submitted by your hospital"
            }), 403
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

# VERIFICATION API

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

# Alerts API

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    try:
        conn = get_db_connection()
        alerts = conn.execute("SELECT * FROM pick_alerts WHERE alert_status = 'ACTIVE' ORDER BY created_at DESC LIMIT 50").fetchall()
        conn.close()
        return jsonify({"alerts": [dict(a) for a in alerts]})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

# DASHBOARD API 

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

# REPORTS API

@app.route('/api/reports/accuracy')
def accuracy_report():
    try:
        report = ReportingSystem(DB_NAME).get_picking_accuracy_report(
            request.args.get('start_date'), request.args.get('end_date')
        )
        return jsonify(report)
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/api/reports/staff-performance')
def staff_performance_report():
    try:
        report = ReportingSystem(DB_NAME).get_staff_performance_report()
        for staff in report.get('data', []):
            staff['total_picks'] = staff.get('total_picks') or 0
            staff['successful_picks'] = staff.get('successful_picks') or 0
            staff['failed_picks'] = staff.get('failed_picks') or 0
            staff['accuracy_rate'] = staff.get('accuracy_rate') or 0
            staff['avg_verification_time'] = staff.get('avg_verification_time') or 0
            staff['performance_status'] = (
                'Accurate' if staff['total_picks'] and staff['accuracy_rate'] >= 95
                else 'Needs improvement' if staff['failed_picks'] else 'No verifications yet'
            )
            staff['error_summary'] = (
                f"{staff['failed_picks']} verification error(s)"
                if staff['failed_picks'] else 'No verification errors'
            )
        return jsonify(report)
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/api/reports/inventory')
def inventory_report():
    try:
        return jsonify(ReportingSystem(DB_NAME).get_inventory_verification_report())
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/api/reports/error-trends')
def error_trends_report():
    try:
        days = max(1, min(int(request.args.get('days', 7)), 365))
        return jsonify(ReportingSystem(DB_NAME).get_error_trend_report(days))
    except (TypeError, ValueError):
        return jsonify({"status": "ERROR", "message": "days must be a positive number"}), 400
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/api/reports/dashboard')
def reports_dashboard():
    try:
        return jsonify(ReportingSystem(DB_NAME).get_compliance_dashboard_data())
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route('/api/audit/staff/<int:staff_id>')
def staff_audit_history(staff_id):
    try:
        days = max(1, min(int(request.args.get('days', 30)), 365))
        report = AuditSystem(DB_NAME).get_staff_audit_history(staff_id, days)
        if report.get('status') == 'ERROR':
            return jsonify(report), 404
        return jsonify(report)
    except (TypeError, ValueError):
        return jsonify({"status": "ERROR", "message": "days must be a positive number"}), 400
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
