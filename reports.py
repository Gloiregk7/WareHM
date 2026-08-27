import sqlite3
from datetime import datetime, timedelta

class ReportingSystem:
    """
    Reporting and Analytics System for KEMSA WMS
    Generates picking accuracy, performance, and trend reports
    """
    
    def __init__(self, db_path):
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_picking_accuracy_report(self, start_date=None, end_date=None):
        """
        Generate picking accuracy report
        
        Args:
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            dict: Accuracy metrics
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            date_filter = ''
            params = []
            
            if start_date and end_date:
                date_filter = ' AND vl.timestamp BETWEEN ? AND ?'
                params = [start_date, end_date]
            
            cursor.execute(f'''
                SELECT 
                    COUNT(*) as total_picks,
                    SUM(CASE WHEN vl.result = 'APPROVED' THEN 1 ELSE 0 END) as approved_picks,
                    SUM(CASE WHEN vl.result = 'REJECTED' THEN 1 ELSE 0 END) as rejected_picks,
                    ROUND(100.0 * SUM(CASE WHEN vl.result = 'APPROVED' THEN 1 ELSE 0 END) / 
                          COUNT(*), 2) as accuracy_percentage
                FROM verification_log vl
                WHERE 1=1 {date_filter}
            ''', params)
            
            result = dict(cursor.fetchone())
            
            # Get error breakdown
            cursor.execute(f'''
                SELECT error_codes, COUNT(*) as count 
                FROM verification_log 
                WHERE result = 'REJECTED' {date_filter}
                GROUP BY error_codes
            ''', params)
            
            error_breakdown = {}
            for row in cursor.fetchall():
                if row['error_codes']:
                    errors = row['error_codes'].split(',')
                    for error in errors:
                        error = error.strip()
                        error_breakdown[error] = error_breakdown.get(error, 0) + 1
            
            conn.close()
            
            return {
                "report_type": "PICKING_ACCURACY",
                "period": {"start": start_date, "end": end_date},
                "metrics": result,
                "error_breakdown": error_breakdown
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def get_staff_performance_report(self, staff_id=None):
        """
        Generate staff performance metrics
        
        Args:
            staff_id: Specific staff ID or None for all staff
            
        Returns:
            dict: Staff performance data
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if staff_id:
                cursor.execute('''
                    SELECT 
                        s.staff_id, s.operator_name, s.employee_id,
                        COUNT(vl.log_id) as total_picks,
                        SUM(CASE WHEN vl.result = 'APPROVED' THEN 1 ELSE 0 END) as successful_picks,
                        SUM(CASE WHEN vl.result = 'REJECTED' THEN 1 ELSE 0 END) as failed_picks,
                        ROUND(100.0 * SUM(CASE WHEN vl.result = 'APPROVED' THEN 1 ELSE 0 END) / 
                              COUNT(vl.log_id), 2) as accuracy_rate,
                        ROUND(AVG(vl.verification_time), 2) as avg_verification_time
                    FROM staff s
                    LEFT JOIN verification_log vl ON s.staff_id = vl.operator_id
                    WHERE s.staff_id = ?
                    GROUP BY s.staff_id
                ''', (staff_id,))
            else:
                cursor.execute('''
                    SELECT 
                        s.staff_id, s.operator_name, s.employee_id,
                        COUNT(vl.log_id) as total_picks,
                        SUM(CASE WHEN vl.result = 'APPROVED' THEN 1 ELSE 0 END) as successful_picks,
                        SUM(CASE WHEN vl.result = 'REJECTED' THEN 1 ELSE 0 END) as failed_picks,
                        ROUND(100.0 * SUM(CASE WHEN vl.result = 'APPROVED' THEN 1 ELSE 0 END) / 
                              COUNT(vl.log_id), 2) as accuracy_rate,
                        ROUND(AVG(vl.verification_time), 2) as avg_verification_time
                    FROM staff s
                    LEFT JOIN verification_log vl ON s.staff_id = vl.operator_id
                    WHERE s.status = 'ACTIVE'
                    GROUP BY s.staff_id
                    ORDER BY accuracy_rate DESC
                ''')
            
            performance = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return {
                "report_type": "STAFF_PERFORMANCE",
                "data": performance
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def get_inventory_verification_report(self):
        """
        Generate inventory verification report
        
        Returns:
            dict: Inventory status
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_items,
                    SUM(quantity) as total_quantity,
                    COUNT(CASE WHEN expiry_date < date('now') THEN 1 END) as expired_items,
                    COUNT(CASE WHEN expiry_date BETWEEN date('now') AND date('now', '+30 days') 
                          THEN 1 END) as expiring_soon
                FROM inventory
            ''')
            
            summary = dict(cursor.fetchone())
            
            # Get low stock items
            cursor.execute('''
                SELECT sku, item_name, quantity, location, expiry_date 
                FROM inventory 
                WHERE quantity < 5
                ORDER BY quantity ASC
            ''')
            
            low_stock = [dict(row) for row in cursor.fetchall()]
            
            # Get expired items
            cursor.execute('''
                SELECT sku, item_name, batch_code, expiry_date, quantity
                FROM inventory 
                WHERE expiry_date < date('now')
                ORDER BY expiry_date
            ''')
            
            expired = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                "report_type": "INVENTORY_VERIFICATION",
                "summary": summary,
                "low_stock_items": low_stock,
                "expired_items": expired
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def get_error_trend_report(self, days=30):
        """
        Get error trends over time
        
        Args:
            days: Number of days to analyze
            
        Returns:
            dict: Error trends
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Daily error counts
            cursor.execute(f'''
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as total_picks,
                    SUM(CASE WHEN result = 'REJECTED' THEN 1 ELSE 0 END) as rejected_picks
                FROM verification_log 
                WHERE timestamp >= datetime('now', '-{days} days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            ''')
            
            daily_data = [dict(row) for row in cursor.fetchall()]
            
            # Common errors
            cursor.execute('''
                SELECT error_codes, COUNT(*) as count 
                FROM verification_log 
                WHERE result = 'REJECTED' AND timestamp >= datetime('now', '-30 days')
                GROUP BY error_codes
                ORDER BY count DESC
                LIMIT 10
            ''')
            
            top_errors = []
            for row in cursor.fetchall():
                if row['error_codes']:
                    errors = row['error_codes'].split(',')
                    for error in errors:
                        error = error.strip()
                        top_errors.append({"error": error, "count": row['count']})
            
            conn.close()
            
            return {
                "report_type": "ERROR_TREND",
                "period_days": days,
                "daily_data": daily_data,
                "top_errors": top_errors
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def get_compliance_dashboard_data(self):
        """
        Get all data needed for compliance dashboard
        
        Returns:
            dict: Dashboard data
        """
        try:
            accuracy_report = self.get_picking_accuracy_report()
            performance_report = self.get_staff_performance_report()
            inventory_report = self.get_inventory_verification_report()
            error_trends = self.get_error_trend_report(7)
            
            return {
                "dashboard_type": "COMPLIANCE",
                "timestamp": datetime.now().isoformat(),
                "accuracy": accuracy_report,
                "performance": performance_report,
                "inventory": inventory_report,
                "error_trends": error_trends
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
