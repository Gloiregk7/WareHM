# KEMSA Vision-Based Picking System

**Automated Vision-Based Picking System for Medical Logistics**

A comprehensive Flask-based Warehouse Management System (WMS) with computer vision-enabled verification for the Kenya Medical Supplies Authority (KEMSA). This system eliminates picking errors through real-time barcode and OCR verification.

---

## 🎯 Project Overview

This project addresses KEMSA's critical picking error problem by implementing:

- **Vision-Based Verification**: Real-time OCR and barcode reading for item verification
- **Real-Time WMS Integration**: Instant inventory updates and order fulfillment
- **Comprehensive Audit Trail**: Complete tracking of all picking transactions
- **Alert System**: Visual and audible alerts for picking errors
- **Staff Performance Tracking**: Individual and team accuracy metrics
- **Advanced Reporting**: Analytics and compliance reports

---

## 📋 Key Features

### 1. **Vision System Module** (`vision_system.py`)
- Barcode reading and data extraction
- Optical Character Recognition (OCR) for batch and expiry dates
- Real-time item verification against orders
- Error detection (SKU mismatch, batch mismatch, expired stock)

### 2. **WMS Integration** (`middleware.py`)
- Device registration and heartbeat monitoring
- Real-time data synchronization between vision system and WMS
- Inventory updates after successful picks
- Message queuing for reliable communication
- System health monitoring

### 3. **Alert System** (`alerts.py`)
- Active alert management
- Multiple alert types (SKU mismatch, batch mismatch, expired stock, etc.)
- Alert severity levels (LOW, MEDIUM, HIGH, CRITICAL)
- Visual and audible alert triggers
- Alert statistics and reporting

### 4. **Audit Trail & Logging** (`audit_system.py`)
- Comprehensive transaction logging
- Action tracking for compliance
- Picking history per order
- Staff activity history
- Compliance report generation

### 5. **Reporting & Analytics** (`reports.py`)
- Picking accuracy reports
- Staff performance metrics
- Inventory verification reports
- Error trend analysis
- Compliance dashboard data

### 6. **API Endpoints** (`app.py`)
- **30+ REST API endpoints** covering all operations
- Staff management
- Order management
- Picking verification
- Alert management
- Audit trail access
- Report generation

---

## 🗄️ Database Schema

### Core Tables:
- **inventory**: Medical supplies inventory with location and expiry tracking
- **staff**: Warehouse staff member information
- **orders**: Picking orders with SKU, batch, and destination
- **verification_log**: Every pick attempt with results
- **audit_trail**: Complete action history for compliance
- **pick_alerts**: Real-time alert management
- **staff_performance**: Performance metrics per staff member

---

## 🚀 Quick Start

### Installation

1. **Clone/Setup Project**:
   ```bash
   cd c:\Users\gloir\Desktop\WarehouseManagement
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize Database**:
   ```bash
   python database.py
   ```

4. **Run Application**:
   ```bash
   python app.py
   ```

The application will start at `http://localhost:5000`

---

## 📱 Web Interfaces

### 1. **Picking Verification Station** (`/verify`)
- Load orders by ID
- Capture images with vision system
- Real-time verification results
- Green (Approved) / Red (Rejected) feedback
- Audible alerts for errors

### 2. **Operations Dashboard** (`/dashboard`)
- Real-time KPIs: Total picks, Approved, Rejected, Accuracy Rate
- Active alerts panel
- Order status summary
- Recent verification logs
- Auto-refresh every 10 seconds

### 3. **Staff Performance Dashboard** (`/staff`)
- Individual staff performance cards
- Accuracy rate tracking
- Pick count and success metrics
- Detailed audit trail per staff member
- 30-day activity history

### 4. **Reports & Analytics** (`/reports`)
- Picking accuracy reports
- Inventory verification status
- Error trends (last 7 days)
- Compliance summary
- Date range filtering
- Export functionality

---

## 🔌 API Endpoints

### Staff Management
- `GET /api/staff` - List all staff
- `POST /api/staff` - Register new staff
- `GET /api/staff/<id>` - Get staff details and performance

### Order Management
- `GET /api/orders` - Get pending orders
- `POST /api/orders` - Create new order
- `GET /api/orders/<id>` - Get order details and alerts

### Picking Verification
- `POST /api/verify` - Main verification endpoint
- `POST /api/verify/batch` - Batch verification

### Alerts
- `GET /api/alerts` - Get active alerts
- `GET /api/alerts/<order_id>` - Get alerts for order
- `PUT /api/alerts/<id>/resolve` - Resolve alert
- `GET /api/alerts/statistics` - Alert statistics

### Audit & Compliance
- `GET /api/audit` - Get audit trail
- `GET /api/audit/order/<id>` - Get order history
- `GET /api/audit/staff/<id>` - Get staff history
- `GET /api/compliance-report` - Generate compliance report

### Reports
- `GET /api/reports/accuracy` - Picking accuracy report
- `GET /api/reports/staff-performance` - Staff performance report
- `GET /api/reports/inventory` - Inventory verification report
- `GET /api/reports/error-trends` - Error trend analysis
- `GET /api/reports/dashboard` - Comprehensive dashboard data

### System
- `GET /api/dashboard` - Main dashboard metrics
- `POST /api/middleware/devices` - Register device
- `GET /api/middleware/status` - System status
- `GET /api/middleware/health` - Device health check
- `POST /api/middleware/heartbeat/<device_id>` - Device heartbeat

---

## 📊 Performance Requirements

As per project proposal:

| Requirement | Target | Implementation |
|---|---|---|
| Error Rate | 0% | Vision verification catches all errors |
| Processing Time | < 2 seconds | Real-time verification |
| System Uptime | 99.5% | Middleware redundancy |
| Usability | < 1 day training | Intuitive UI |
| Accuracy | 100% | Multi-layer verification |

---

## 🔐 Audit & Compliance

### Audit Trail Features:
- **User Tracking**: Staff ID, timestamp, action details
- **Order Tracking**: Complete picking history per order
- **Error Tracking**: All failed picks logged with reasons
- **Performance Metrics**: Accuracy rates, staff performance
- **Compliance Reports**: Generate for audit purposes

### Compliance Reports Include:
- Transaction summaries
- Staff activity counts
- Error analysis
- Accuracy metrics
- Date range filtering

---

## 🛠️ Technical Stack

| Component | Technology |
|---|---|
| Backend Framework | Flask 3.1.3 |
| Database | SQLite3 |
| Computer Vision | OpenCV, Tesseract OCR, pyzbar |
| Frontend | Bootstrap 5, JavaScript |
| APIs | RESTful architecture |

---

## 📝 Sample Data

The system initializes with:
- **4 Staff Members**: Different departments and roles
- **5 Inventory Items**: Medical supplies with batch/expiry info
- **4 Sample Orders**: Ready for picking verification

---

## 🔄 Workflow Example

1. **Order Loading**: Staff selects order ID → System displays required item details
2. **Image Capture**: Place item under camera → Vision system captures image
3. **Verification**: OCR extracts barcode, batch, expiry → Compares with order
4. **Result**:
   - ✅ **APPROVED**: Green signal, audible beep, inventory updated, audit logged
   - ❌ **REJECTED**: Red signal, error alert, pick not recorded, alert created
5. **Reporting**: Supervisors monitor accuracy, staff performance, inventory status

---

## 📈 Metrics Tracked

### System-Level:
- Total picks processed
- Approval/rejection rates
- Overall accuracy percentage
- Active alerts count
- Orders pending/completed

### Staff-Level:
- Individual accuracy rate
- Total picks per staff
- Successful vs failed picks
- Average verification time
- Error patterns

### Inventory-Level:
- Low stock items
- Expired items
- Expiring soon
- Stock quantity by location

---

## 🐛 Error Codes

| Code | Meaning | Severity |
|---|---|---|
| SKU_MISMATCH | Wrong item scanned | CRITICAL |
| BATCH_MISMATCH | Wrong batch number | CRITICAL |
| EXPIRED_STOCK | Item past expiry date | CRITICAL |
| QUANTITY_MISMATCH | Wrong quantity picked | HIGH |
| WRONG_DOSAGE | Wrong medication strength | CRITICAL |
| SYSTEM_ERROR | Technical issue | HIGH |

---

## 🔊 Alert System

### Visual Alerts:
- Green background: APPROVED
- Red background: REJECTED
- Yellow border: Active alerts panel

### Audible Alerts:
- **Success**: Single 800Hz beep (0.5s)
- **Error**: Triple 2000Hz beep (0.1s each)
- Adjustable by severity level

---

## 📦 Deployment

For production deployment:

1. Update `app.py`: Change `debug=False`
2. Configure database path for centralized storage
3. Set up device heartbeat monitoring
4. Configure alert thresholds
5. Set up email/SMS for critical alerts
6. Enable HTTPS for security
7. Set up database backups

---

## 🤝 Integration Points

The system integrates with:
- **Hardware**: USB cameras, barcode scanners, pick-to-light systems
- **Existing WMS**: Real-time inventory sync
- **HR System**: Staff data sync
- **Reporting Tools**: Excel, PDF export

---

## 📚 Module Documentation

Each module includes comprehensive documentation:
- `vision_system.py`: Computer vision processing
- `middleware.py`: Hardware and WMS integration
- `alerts.py`: Alert management and triggers
- `audit_system.py`: Compliance and audit trails
- `reports.py`: Analytics and reporting
- `app.py`: API endpoints and routing

---

## ✅ Testing Checklist

- [ ] Database initialization completes
- [ ] All sample data loads correctly
- [ ] Vision system processes test images
- [ ] Verification logic detects all error types
- [ ] Alerts trigger on failures
- [ ] Audit trail records all transactions
- [ ] Reports generate correct metrics
- [ ] Dashboard updates in real-time
- [ ] Staff dashboard shows performance
- [ ] APIs respond within latency requirements

---

## 📞 Support

For issues or questions:
1. Check the API documentation above
2. Review database schema
3. Verify all dependencies are installed
4. Check browser console for JavaScript errors
5. Review Flask debug logs

---

## 🎓 Academic Reference

**Project Type**: Software Engineering II - Group Project
**Client**: Kenya Medical Supplies Authority (KEMSA)
**Methodology**: V-Model (Verification & Validation)
**Team Members**: 
- Allan Kamau (SCT221-0673/2022)
- Gloire Mugisha (SCT221-0971/2021)
- Stacy Wangeci (SCT221-0635/2023)
- Mary Cynthia Gitau (SCT221-0730/2023)

**Institution**: Jomo Kenyatta University of Agriculture and Technology (JKUAT)
**Date**: August 2026

---

## 📄 License

This project is developed for KEMSA as part of academic coursework.

---

**Last Updated**: August 27, 2026
**Version**: 1.0.0 - Full Implementation
