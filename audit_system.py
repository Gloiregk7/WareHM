import sqlite3
from datetime import datetime

class AuditSystem:
    """
    Comprehensive Audit Trail System for KEMSA WMS
    Tracks all picking operations and system events
    """
    
    def __init__(self, db_path):
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def log_picking_transaction(self, staff_id, order_id, sku, scanned_batch, scanned_expiry, 
                               result, error_codes, station_id, verification_time):
        """
        Log a picking transaction
        
        Args:
            staff_id: Staff member ID
            order_id: Order ID
            sku: Item SKU
            scanned_batch: Scanned batch code
            scanned_expiry: Scanned expiry date
            result: APPROVED or REJECTED
            error_codes: Comma-separated error codes
            station_id: Verification station ID
            verification_time: Time taken for verification
            
        Returns:
            dict: Logging result
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO verification_log 
                (order_id, sku, scanned_batch, scanned_expiry, result, error_codes, 
                 operator_id, station_id, verification_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, sku, scanned_batch, scanned_expiry, result, error_codes,
                  staff_id, station_id, verification_time))
            
            # Log to audit trail
            action = f"PICK_{result}"
            self.log_action(staff_id, order_id, action, None, result, 
                          f"Batch: {scanned_batch}, Expiry: {scanned_expiry}, Errors: {error_codes}")
            
            conn.commit()
            log_id = cursor.lastrowid
            conn.close()
            
            return {
                "status": "SUCCESS",
                "log_id": log_id,
                "message": f"Transaction logged: {result}"
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def log_action(self, staff_id, order_id, action, old_value, new_value, details):
        """
        Log a general action to audit trail
        
        Args:
            staff_id: Staff member ID
            order_id: Order ID
            action: Action type
            old_value: Previous value
            new_value: New value
            details: Additional details
            
        Returns:
            dict: Logging result
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO audit_trail 
                (staff_id, order_id, action, old_value, new_value, status, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (staff_id, order_id, action, old_value, new_value, 'RECORDED', details))
            
            conn.commit()
            audit_id = cursor.lastrowid
            conn.close()
            
            return {"status": "SUCCESS", "audit_id": audit_id}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def get_audit_trail(self, order_id=None, staff_id=None, action=None, limit=100):
        """
        Retrieve audit trail records
        
        Args:
            order_id: Filter by order (optional)
            staff_id: Filter by staff (optional)
            action: Filter by action (optional)
            limit: Max records to return
            
        Returns:
            list: Audit records
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = 'SELECT * FROM audit_trail WHERE 1=1'
            params = []
            
            if order_id:
                query += ' AND order_id = ?'
                params.append(order_id)
            if staff_id:
                query += ' AND staff_id = ?'
                params.append(staff_id)
            if action:
                query += ' AND action = ?'
                params.append(action)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            records = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return records
        except Exception as e:
            return []
    
    def get_picking_history(self, order_id):
        """
        Get complete picking history for an order
        
        Args:
            order_id: Order ID
            
        Returns:
            dict: Complete history with all attempts
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get order info
            cursor.execute('''
                SELECT o.*, s.operator_name 
                FROM orders o
                LEFT JOIN staff s ON o.assigned_to = s.staff_id
                WHERE o.order_id = ?
            ''', (order_id,))
            order = dict(cursor.fetchone())
            
            # Get verification logs
            cursor.execute('''
                SELECT vl.*, s.operator_name 
                FROM verification_log vl
                LEFT JOIN staff s ON vl.operator_id = s.staff_id
                WHERE vl.order_id = ?
                ORDER BY vl.timestamp
            ''', (order_id,))
            verifications = [dict(row) for row in cursor.fetchall()]
            
            # Get audit trail
            cursor.execute('''
                SELECT * FROM audit_trail 
                WHERE order_id = ?
                ORDER BY timestamp
            ''', (order_id,))
            actions = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                "order": order,
                "verification_log": verifications,
                "audit_trail": actions,
                "status": "COMPLETE"
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def get_staff_audit_history(self, staff_id, days=30):
        """
        Get audit history for a staff member
        
        Args:
            staff_id: Staff ID
            days: Number of days to look back
            
        Returns:
            dict: Staff activity summary
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get staff info
            cursor.execute('SELECT * FROM staff WHERE staff_id = ?', (staff_id,))
            staff = dict(cursor.fetchone())
            
            # Get actions
            cursor.execute('''
                SELECT * FROM audit_trail 
                WHERE staff_id = ? AND timestamp >= datetime('now', '-' || ? || ' days')
                ORDER BY timestamp DESC
            ''', (staff_id, days))
            actions = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                "staff": staff,
                "actions": actions,
                "period_days": days
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def generate_compliance_report(self, start_date=None, end_date=None):
        """
        Generate compliance report for audit purposes
        
        Args:
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            dict: Compliance report
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            date_filter = ''
            params = []
            
            if start_date and end_date:
                date_filter = ' WHERE timestamp BETWEEN ? AND ?'
                params = [start_date, end_date]
            
            # Get summary stats
            cursor.execute(f'''
                SELECT 
                    COUNT(*) as total_transactions,
                    SUM(CASE WHEN action LIKE 'PICK_APPROVED%' THEN 1 ELSE 0 END) as approved_picks,
                    SUM(CASE WHEN action LIKE 'PICK_REJECTED%' THEN 1 ELSE 0 END) as rejected_picks
                FROM audit_trail {date_filter}
            ''', params)
            
            summary = dict(cursor.fetchone())
            
            # Get staff action counts
            cursor.execute(f'''
                SELECT staff_id, COUNT(*) as action_count 
                FROM audit_trail {date_filter}
                GROUP BY staff_id
            ''', params)
            
            staff_activity = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                "report_type": "COMPLIANCE",
                "period": {"start": start_date, "end": end_date},
                "summary": summary,
                "staff_activity": staff_activity
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
