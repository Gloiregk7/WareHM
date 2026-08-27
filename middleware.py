import json
import time
import queue
import threading
from datetime import datetime

class Middleware:
    """
    Middleware Integration Layer for KEMSA WMS
    Handles communication between Vision System, WMS, and Hardware Components
    """
    
    def __init__(self, db_connection=None):
        self.db_conn = db_connection
        self.message_queue = queue.Queue()
        self.running = True
        self.devices = {}
        self.last_sync_time = None
        self.sync_latency = 0.0
    
    def register_device(self, device_id, device_type, endpoint):
        """
        Register a hardware device with middleware
        
        Args:
            device_id: Unique device identifier
            device_type: Type of device (camera, scanner, light_system)
            endpoint: Device endpoint/address
            
        Returns:
            dict: Registration result
        """
        try:
            self.devices[device_id] = {
                "type": device_type,
                "endpoint": endpoint,
                "status": "CONNECTED",
                "registered_at": datetime.now().isoformat(),
                "last_heartbeat": datetime.now().isoformat()
            }
            
            return {
                "status": "SUCCESS",
                "message": f"Device {device_id} registered",
                "device_id": device_id
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def send_to_device(self, device_id, message_type, data):
        """
        Send message to a device
        
        Args:
            device_id: Target device ID
            message_type: Type of message
            data: Message payload
            
        Returns:
            dict: Send result
        """
        try:
            if device_id not in self.devices:
                return {"status": "ERROR", "message": f"Device {device_id} not found"}
            
            message = {
                "device_id": device_id,
                "type": message_type,
                "payload": data,
                "timestamp": datetime.now().isoformat(),
                "id": f"{device_id}_{int(time.time()*1000)}"
            }
            
            self.message_queue.put(message)
            
            return {
                "status": "SUCCESS",
                "message_id": message["id"],
                "message": "Message queued for delivery"
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def broadcast_to_all_devices(self, message_type, data):
        """
        Broadcast message to all registered devices
        
        Args:
            message_type: Type of message
            data: Message payload
            
        Returns:
            dict: Broadcast result
        """
        try:
            broadcast_ids = []
            for device_id in self.devices.keys():
                result = self.send_to_device(device_id, message_type, data)
                if result["status"] == "SUCCESS":
                    broadcast_ids.append(device_id)
            
            return {
                "status": "SUCCESS",
                "message": f"Broadcast sent to {len(broadcast_ids)} devices",
                "devices": broadcast_ids
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def sync_wms_data(self, vision_result, order_data):
        """
        Synchronize data between Vision System and WMS
        Ensures real-time data consistency
        
        Args:
            vision_result: Result from vision system
            order_data: Current order data from WMS
            
        Returns:
            dict: Sync result
        """
        start_time = time.time()
        try:
            sync_data = {
                "order_id": order_data.get("order_id"),
                "vision_result": vision_result,
                "wms_data": order_data,
                "verification_status": vision_result.get("status"),
                "timestamp": datetime.now().isoformat()
            }
            
            # Simulate data sync
            self.last_sync_time = datetime.now().isoformat()
            self.sync_latency = round((time.time() - start_time) * 1000, 2)  # ms
            
            if self.sync_latency > 1000:  # More than 1 second
                return {
                    "status": "WARNING",
                    "message": "Sync latency exceeded threshold",
                    "latency_ms": self.sync_latency,
                    "data": sync_data
                }
            
            return {
                "status": "SUCCESS",
                "message": "Data synchronized",
                "latency_ms": self.sync_latency,
                "data": sync_data
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def update_inventory(self, order_id, sku, action):
        """
        Update inventory after pick
        
        Args:
            order_id: Order ID
            sku: Item SKU
            action: Action (PICK, RETURN, ADJUST)
            
        Returns:
            dict: Update result
        """
        try:
            update_record = {
                "order_id": order_id,
                "sku": sku,
                "action": action,
                "timestamp": datetime.now().isoformat()
            }
            
            # Would execute in actual DB
            return {
                "status": "SUCCESS",
                "message": f"Inventory updated: {action}",
                "record": update_record
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def get_system_status(self):
        """
        Get overall system status
        
        Returns:
            dict: System health status
        """
        try:
            connected_devices = sum(1 for d in self.devices.values() if d["status"] == "CONNECTED")
            
            return {
                "system_status": "OPERATIONAL" if connected_devices > 0 else "DEGRADED",
                "timestamp": datetime.now().isoformat(),
                "devices": {
                    "total": len(self.devices),
                    "connected": connected_devices,
                    "list": self.devices
                },
                "message_queue_size": self.message_queue.qsize(),
                "last_sync": self.last_sync_time,
                "average_latency_ms": self.sync_latency
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def handle_device_heartbeat(self, device_id):
        """
        Handle heartbeat from device
        
        Args:
            device_id: Device ID
            
        Returns:
            dict: Heartbeat result
        """
        try:
            if device_id in self.devices:
                self.devices[device_id]["last_heartbeat"] = datetime.now().isoformat()
                self.devices[device_id]["status"] = "CONNECTED"
                
                return {
                    "status": "SUCCESS",
                    "message": "Heartbeat acknowledged"
                }
            else:
                return {
                    "status": "ERROR",
                    "message": f"Device {device_id} not registered"
                }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def check_device_health(self):
        """
        Check health of all connected devices
        
        Returns:
            dict: Health status
        """
        try:
            health_status = {}
            timeout_seconds = 30
            
            for device_id, device_info in self.devices.items():
                last_heartbeat = datetime.fromisoformat(device_info["last_heartbeat"])
                elapsed = (datetime.now() - last_heartbeat).total_seconds()
                
                if elapsed > timeout_seconds:
                    health_status[device_id] = "OFFLINE"
                    self.devices[device_id]["status"] = "DISCONNECTED"
                else:
                    health_status[device_id] = "ONLINE"
            
            return {
                "status": "SUCCESS",
                "health_check_time": datetime.now().isoformat(),
                "device_health": health_status
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
