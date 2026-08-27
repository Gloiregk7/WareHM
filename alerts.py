import sqlite3
from datetime import datetime
from enum import Enum

class AlertType(Enum):
    """Alert type classifications"""
    SKU_MISMATCH = "SKU_MISMATCH"
    BATCH_MISMATCH = "BATCH_MISMATCH"
    EXPIRED_STOCK = "EXPIRED_STOCK"
    QUANTITY_MISMATCH = "QUANTITY_MISMATCH"
    WRONG_DOSAGE = "WRONG_DOSAGE"
    PICKING_ERROR = "PICKING_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AlertSystem:
    """
    Alert System for KEMSA WMS
    Manages real-time alerts for picking errors and system events
    """
    
    def __init__(self, db_path):
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_alert(self, order_id, alert_type, alert_code, alert_message, severity="HIGH"):
        """
        Create a new alert
        
        Args:
            order_id: Order ID
            alert_type: Type of alert
            alert_code: Alert code
            alert_message: Alert message
            severity: Alert severity level
            
        Returns:
            dict: Alert creation result
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO pick_alerts (order_id, alert_type, alert_code, alert_message, severity)
                VALUES (?, ?, ?, ?, ?)
            ''', (order_id, alert_type, alert_code, alert_message, severity))
            
            conn.commit()
            alert_id = cursor.lastrowid
            conn.close()
            
            return {
                "status": "SUCCESS",
                "alert_id": alert_id,
                "message": f"Alert created: {alert_message}"
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def get_active_alerts(self, limit=50):
        """
        Get all active alerts
        
        Args:
            limit: Max number of alerts to return
            
        Returns:
            list: Active alerts
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT pa.*, o.item_name, o.sku 
                FROM pick_alerts pa
                JOIN orders o ON pa.order_id = o.order_id
                WHERE pa.alert_status = 'ACTIVE'
                ORDER BY pa.created_at DESC
                LIMIT ?
            ''', (limit,))
            
            alerts = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return alerts
        except Exception as e:
            return []
    
    def get_alerts_by_order(self, order_id):
        """
        Get all alerts for a specific order
        
        Args:
            order_id: Order ID
            
        Returns:
            list: Alerts for the order
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM pick_alerts 
                WHERE order_id = ?
                ORDER BY created_at DESC
            ''', (order_id,))
            
            alerts = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return alerts
        except Exception as e:
            return []
    
    def resolve_alert(self, alert_id):
        """
        Resolve an alert
        
        Args:
            alert_id: Alert ID
            
        Returns:
            dict: Resolution result
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE pick_alerts 
                SET alert_status = 'RESOLVED', resolved_at = datetime('now')
                WHERE alert_id = ?
            ''', (alert_id,))
            
            conn.commit()
            conn.close()
            
            return {"status": "SUCCESS", "message": "Alert resolved"}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def get_alert_statistics(self):
        """
        Get alert statistics
        
        Returns:
            dict: Alert statistics
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Total alerts
            cursor.execute('SELECT COUNT(*) as count FROM pick_alerts')
            total = cursor.fetchone()['count']
            
            # Active alerts
            cursor.execute("SELECT COUNT(*) as count FROM pick_alerts WHERE alert_status = 'ACTIVE'")
            active = cursor.fetchone()['count']
            
            # Alerts by severity
            cursor.execute('''
                SELECT severity, COUNT(*) as count 
                FROM pick_alerts 
                WHERE alert_status = 'ACTIVE'
                GROUP BY severity
            ''')
            by_severity = {row['severity']: row['count'] for row in cursor.fetchall()}
            
            # Alerts by type
            cursor.execute('''
                SELECT alert_type, COUNT(*) as count 
                FROM pick_alerts 
                WHERE alert_status = 'ACTIVE'
                GROUP BY alert_type
            ''')
            by_type = {row['alert_type']: row['count'] for row in cursor.fetchall()}
            
            conn.close()
            
            return {
                "total_alerts": total,
                "active_alerts": active,
                "by_severity": by_severity,
                "by_type": by_type
            }
        except Exception as e:
            return {}
    
    def trigger_visual_alert(self, alert_type, message):
        """
        Trigger visual alert (for UI feedback)
        
        Returns:
            dict: Alert display data
        """
        color_map = {
            "SKU_MISMATCH": "#FF0000",
            "BATCH_MISMATCH": "#FF0000",
            "EXPIRED_STOCK": "#FF0000",
            "PICKING_ERROR": "#FF5500",
            "SYSTEM_ERROR": "#FFB600"
        }
        
        return {
            "type": alert_type,
            "message": message,
            "color": color_map.get(alert_type, "#FF0000"),
            "display": "REJECTED"
        }
    
    def trigger_audible_alert(self, severity):
        """
        Generate audible alert parameters
        
        Args:
            severity: Severity level
            
        Returns:
            dict: Audio alert configuration
        """
        sound_map = {
            "CRITICAL": {"frequency": 2000, "duration": 1.0, "count": 3},
            "HIGH": {"frequency": 1500, "duration": 0.5, "count": 2},
            "MEDIUM": {"frequency": 1000, "duration": 0.3, "count": 1},
            "LOW": {"frequency": 500, "duration": 0.2, "count": 1}
        }
        
        return sound_map.get(severity, sound_map["HIGH"])
