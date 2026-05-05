# API Quick Reference Guide

Quick reference for common API operations.

---

## 🔑 Authentication

### Get Access Token
```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "password"
  }'
```

**Response:**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Refresh Token
```bash
curl -X POST http://localhost:8000/api/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "refresh_token_here"}'
```

### Using Token in Requests
```bash
curl -H "Authorization: Bearer ACCESS_TOKEN" \
  http://localhost:8000/api/endpoint/
```

---

## 👥 User Management

### Create User (HEAD_OFFICE only)
```bash
curl -X POST http://localhost:8000/api/users/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "SecurePass123",
    "role": "EMPLOYEE"
  }'
```

### List Users
```bash
curl http://localhost:8000/api/users/ \
  -H "Authorization: Bearer TOKEN"
```

### Get Specific User
```bash
curl http://localhost:8000/api/users/1/ \
  -H "Authorization: Bearer TOKEN"
```

---

## 🏢 Branch & Department

### Create Branch
```bash
curl -X POST http://localhost:8000/api/branches/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New York Branch",
    "location": "NYC",
    "manager": 1
  }'
```

### List Branches
```bash
curl http://localhost:8000/api/branches/ \
  -H "Authorization: Bearer TOKEN"
```

### Create Department
```bash
curl -X POST http://localhost:8000/api/departments/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Engineering",
    "branch": 1
  }'
```

---

## 👨‍💼 Employee Management

### Create Employee
```bash
curl -X POST http://localhost:8000/api/employees/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user": 2,
    "full_name": "John Doe",
    "position": "Software Engineer",
    "branch": 1,
    "department": 1,
    "status": "ACTIVE",
    "hire_date": "2024-01-01"
  }'
```

### List Employees
```bash
curl http://localhost:8000/api/employees/ \
  -H "Authorization: Bearer TOKEN"
```

### Filter Employees by Branch
```bash
curl "http://localhost:8000/api/employees/?branch=1" \
  -H "Authorization: Bearer TOKEN"
```

### Search Employees
```bash
curl "http://localhost:8000/api/employees/?search=John" \
  -H "Authorization: Bearer TOKEN"
```

### Mark Employee as Exited
```bash
curl -X POST http://localhost:8000/api/employees/1/set_exit_status/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"exit_date": "2024-12-31"}'
```

---

## 💻 Device Management

### Create Device
```bash
curl -X POST http://localhost:8000/api/devices/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_type": "Laptop",
    "brand": "Dell",
    "model": "XPS 13",
    "serial_number": "SN123456",
    "company_tag": "QR001",
    "purchase_date": "2024-01-01",
    "warranty_expiry": "2026-01-01",
    "location_type": "HEAD_OFFICE",
    "current_location": "Head Office"
  }'
```

### List Devices
```bash
curl http://localhost:8000/api/devices/ \
  -H "Authorization: Bearer TOKEN"
```

### Filter Devices by Status
```bash
curl "http://localhost:8000/api/devices/?status=AVAILABLE" \
  -H "Authorization: Bearer TOKEN"
```

### Search Devices
```bash
curl "http://localhost:8000/api/devices/?search=QR001" \
  -H "Authorization: Bearer TOKEN"
```

### Get Device Details
```bash
curl http://localhost:8000/api/devices/1/ \
  -H "Authorization: Bearer TOKEN"
```

---

## 📦 Device Assignment

### Assign Device to Employee
```bash
curl -X POST http://localhost:8000/api/assignments/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": 1,
    "employee_id": 1,
    "condition_on_issue": "Good condition"
  }'
```

### List Assignments
```bash
curl http://localhost:8000/api/assignments/ \
  -H "Authorization: Bearer TOKEN"
```

### List Active Assignments
```bash
curl "http://localhost:8000/api/assignments/?returned_date__isnull=true" \
  -H "Authorization: Bearer TOKEN"
```

### Return Device
```bash
curl -X POST http://localhost:8000/api/assignments/1/return_device/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"condition_on_return": "Minor scratches"}'
```

---

## 🔧 Repair Management

### Request Repair (Employee)
```bash
curl -X POST http://localhost:8000/api/repair-requests/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": 1,
    "issue_description": "Screen flickering",
    "priority": "HIGH"
  }'
```

### List Repair Requests
```bash
curl http://localhost:8000/api/repair-requests/ \
  -H "Authorization: Bearer TOKEN"
```

### Filter by Status
```bash
curl "http://localhost:8000/api/repair-requests/?status=PENDING" \
  -H "Authorization: Bearer TOKEN"
```

### Approve Repair Request (HEAD_OFFICE)
```bash
curl -X POST http://localhost:8000/api/repair-requests/1/approve/ \
  -H "Authorization: Bearer TOKEN"
```

### Reject Repair Request (HEAD_OFFICE)
```bash
curl -X POST http://localhost:8000/api/repair-requests/1/reject/ \
  -H "Authorization: Bearer TOKEN"
```

### Complete Repair (Technician)
```bash
curl -X POST http://localhost:8000/api/repair-logs/1/update_repair/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Replaced screen, tested working",
    "parts_used": "LCD Screen - model X"
  }'
```

---

## 📊 Inventory Management

### Create Inventory Session (HEAD_OFFICE)
```bash
curl -X POST http://localhost:8000/api/inventory-sessions/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"branch_id": 1}'
```

### List Inventory Sessions
```bash
curl http://localhost:8000/api/inventory-sessions/ \
  -H "Authorization: Bearer TOKEN"
```

### List Inventory Items
```bash
curl http://localhost:8000/api/inventory-items/ \
  -H "Authorization: Bearer TOKEN"
```

### Mark Item as Verified (Branch Manager)
```bash
curl -X POST http://localhost:8000/api/inventory-items/1/mark_verified/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"comment": "Device found and working"}'
```

### Mark Item as Missing (Branch Manager)
```bash
curl -X POST http://localhost:8000/api/inventory-items/1/mark_missing/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"comment": "Device not found"}'
```

---

## 🔔 Notifications

### List My Notifications
```bash
curl http://localhost:8000/api/notifications/ \
  -H "Authorization: Bearer TOKEN"
```

### Mark Notification as Read
```bash
curl -X POST http://localhost:8000/api/notifications/1/mark_as_read/ \
  -H "Authorization: Bearer TOKEN"
```

---

## 📋 Audit Logs

### List Audit Logs (HEAD_OFFICE only)
```bash
curl http://localhost:8000/api/audit-logs/ \
  -H "Authorization: Bearer TOKEN"
```

### Filter by Action
```bash
curl "http://localhost:8000/api/audit-logs/?action=DEVICE_ASSIGNED" \
  -H "Authorization: Bearer TOKEN"
```

### Search Audit Logs
```bash
curl "http://localhost:8000/api/audit-logs/?search=device" \
  -H "Authorization: Bearer TOKEN"
```

---

## 🔍 Common Query Parameters

### Pagination
```bash
?page=2
```

### Search
```bash
?search=keyword
```

### Filter
```bash
?status=ACTIVE
?branch=1
?device_type=Laptop
```

### Ordering
```bash
?ordering=name
?ordering=-created_date
```

### Combine Multiple Parameters
```bash
?branch=1&status=ACTIVE&search=John&ordering=name&page=2
```

---

## 📊 Useful Filters

### Get All Available Devices
```bash
/api/devices/?status=AVAILABLE
```

### Get All Active Assignments
```bash
/api/assignments/?returned_date__isnull=true
```

### Get Pending Repairs
```bash
/api/repair-requests/?status=PENDING
```

### Get Employee by Branch
```bash
/api/employees/?branch=1
```

### Get Missing Inventory Items
```bash
/api/inventory-items/?status=MISSING
```

---

## 🛠️ Error Handling

### Common Errors

**400 Bad Request**
```json
{"error": "Device is already assigned to someone"}
```

**401 Unauthorized**
```json
{"detail": "Authentication credentials were not provided."}
```

**403 Forbidden**
```json
{"detail": "Only Head Office staff can access this resource."}
```

**404 Not Found**
```json
{"detail": "Not found."}
```

---

## 💡 Common Workflows

### Workflow 1: Assign Device
```bash
# 1. Get available devices
curl "http://localhost:8000/api/devices/?status=AVAILABLE" \
  -H "Authorization: Bearer TOKEN"

# 2. Assign device
curl -X POST http://localhost:8000/api/assignments/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id":1,"employee_id":1}'

# 3. Check assignment
curl http://localhost:8000/api/assignments/1/ \
  -H "Authorization: Bearer TOKEN"
```

### Workflow 2: Request and Complete Repair
```bash
# 1. Employee requests repair
curl -X POST http://localhost:8000/api/repair-requests/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id":1,
    "issue_description":"Not working",
    "priority":"HIGH"
  }'

# 2. HEAD_OFFICE approves
curl -X POST http://localhost:8000/api/repair-requests/1/approve/ \
  -H "Authorization: Bearer TOKEN"

# 3. Technician completes
curl -X POST http://localhost:8000/api/repair-logs/1/update_repair/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes":"Fixed"}'
```

### Workflow 3: Inventory Check
```bash
# 1. Create session
curl -X POST http://localhost:8000/api/inventory-sessions/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"branch_id":1}'

# 2. Get items
curl "http://localhost:8000/api/inventory-items/?session=1" \
  -H "Authorization: Bearer TOKEN"

# 3. Mark items
curl -X POST http://localhost:8000/api/inventory-items/1/mark_verified/ \
  -H "Authorization: Bearer TOKEN"
```

---

## 🎯 Testing Quick Commands

### Using curl with variables
```bash
# Store token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' | grep -o '"access":"[^"]*"' | cut -d'"' -f4)

# Use token
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/devices/
```

### Using jq for JSON parsing
```bash
# Pretty print response
curl http://localhost:8000/api/devices/ \
  -H "Authorization: Bearer TOKEN" | jq

# Extract specific field
curl http://localhost:8000/api/devices/ \
  -H "Authorization: Bearer TOKEN" | jq '.results[0].company_tag'
```

---

## 📚 Additional Resources

- Full API Documentation: See `API_DOCUMENTATION.md`
- Setup Guide: See `README.md`
- Implementation Details: See `IMPLEMENTATION_SUMMARY.md`
- Code Examples: See `App/views.py` and `App/services.py`

---

**Last Updated:** January 2024
**Version:** 1.0
