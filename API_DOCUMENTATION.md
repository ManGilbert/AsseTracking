# Device Management System API Documentation

## Overview

This API provides a complete management system for device lifecycle, employee management, repairs, and inventory tracking with role-based access control.

**Base URL:** `http://localhost:8000/api/`

---

## Authentication

All endpoints require JWT authentication (except token endpoints).

### Get Access Token

```
POST /api/auth/token/
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}

Response:
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Refresh Access Token

```
POST /api/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "your_refresh_token"
}
```

### Use Token in Requests

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

---

## User Roles & Permissions

### Role Types
- **HEAD_OFFICE**: Admin with full access
- **BRANCH_MANAGER**: Manages branch operations and inventory
- **TECHNICIAN**: Handles device repairs
- **EMPLOYEE**: Uses assigned devices and requests repairs

### Permission Matrix

| Action | HEAD_OFFICE | BRANCH_MANAGER | TECHNICIAN | EMPLOYEE |
|--------|:-----------:|:--------------:|:----------:|:--------:|
| Create Device | ✓ | ✗ | ✗ | ✗ |
| Assign Device | ✓ | ✗ | ✗ | ✗ |
| Return Device | ✓ | ✗ | ✗ | ✗ |
| Create Repair Request | ✗ | ✗ | ✗ | ✓ |
| Approve/Reject Repair | ✓ | ✗ | ✗ | ✗ |
| Update Repair Log | ✗ | ✗ | ✓ | ✗ |
| Create Inventory Session | ✓ | ✗ | ✗ | ✗ |
| Verify Inventory | ✗ | ✓ | ✗ | ✗ |
| View Audit Logs | ✓ | ✗ | ✗ | ✗ |

---

## API Endpoints

### 1. USERS

#### List Users
```
GET /api/users/
Permission: HEAD_OFFICE

Query Parameters:
- search: Search by username or email
- page: Page number (pagination)

Response: [
  {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "HEAD_OFFICE",
    "is_active": true,
    "date_joined": "2024-01-01T10:00:00Z"
  }
]
```

#### Create User
```
POST /api/users/
Permission: HEAD_OFFICE

Body:
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "securepassword123",
  "role": "EMPLOYEE"
}

Response: {
  "id": 2,
  "username": "newuser",
  "email": "newuser@example.com",
  "role": "EMPLOYEE",
  "is_active": true,
  "date_joined": "2024-01-15T10:30:00Z"
}
```

#### Get User
```
GET /api/users/{id}/
Permission: Authenticated

Response: {
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "role": "HEAD_OFFICE",
  "is_active": true,
  "date_joined": "2024-01-01T10:00:00Z"
}
```

---

### 2. BRANCHES

#### List Branches
```
GET /api/branches/
Permission: Authenticated

Query Parameters:
- search: Search by name or location
- ordering: Order by name
- page: Page number

Response: [
  {
    "id": 1,
    "name": "Main Branch",
    "location": "New York",
    "manager": 5,
    "manager_name": "John Manager"
  }
]
```

#### Create Branch
```
POST /api/branches/
Permission: HEAD_OFFICE

Body:
{
  "name": "New Branch",
  "location": "Los Angeles",
  "manager": 5
}

Response: {
  "id": 2,
  "name": "New Branch",
  "location": "Los Angeles",
  "manager": 5,
  "manager_name": "John Manager"
}
```

---

### 3. EMPLOYEES

#### List Employees
```
GET /api/employees/
Permission: Authenticated

Query Parameters:
- branch: Filter by branch ID
- status: Filter by status (ACTIVE, INACTIVE, EXITED)
- search: Search by full_name or position
- page: Page number

Response: [
  {
    "id": 1,
    "full_name": "Jane Doe",
    "position": "Software Engineer",
    "branch_name": "Main Branch",
    "status": "ACTIVE"
  }
]
```

#### Create Employee
```
POST /api/employees/
Permission: HEAD_OFFICE

Body:
{
  "user": 1,
  "full_name": "Jane Doe",
  "position": "Software Engineer",
  "branch": 1,
  "department": 1,
  "status": "ACTIVE",
  "hire_date": "2024-01-01"
}

Response: {
  "id": 1,
  "user": 1,
  "user_username": "janedoe",
  "full_name": "Jane Doe",
  "position": "Software Engineer",
  "branch": 1,
  "branch_name": "Main Branch",
  "department": 1,
  "department_name": "Engineering",
  "status": "ACTIVE",
  "hire_date": "2024-01-01",
  "exit_date": null
}
```

#### Mark Employee as Exited
```
POST /api/employees/{id}/set_exit_status/
Permission: HEAD_OFFICE

Body:
{
  "exit_date": "2024-12-31"
}

Response: {
  "message": "Employee marked as exited. 2 devices marked for return.",
  "affected_devices": 2
}

Note: This automatically marks all assigned devices as PENDING_RETURN
```

---

### 4. DEVICES

#### List Devices
```
GET /api/devices/
Permission: Authenticated

Query Parameters:
- status: Filter by status (AVAILABLE, ASSIGNED, IN_REPAIR, MISSING, etc.)
- device_type: Filter by type
- assigned_branch: Filter by branch
- search: Search by serial_number, company_tag, or model
- ordering: Order by status or purchase_date
- page: Page number

Response: [
  {
    "id": 1,
    "device_type": "Laptop",
    "brand": "Dell",
    "model": "XPS 13",
    "serial_number": "SN12345",
    "company_tag": "QR001",
    "status": "ASSIGNED",
    "assigned_employee": 1,
    "assigned_employee_name": "Jane Doe",
    "assigned_branch": 1,
    "assigned_branch_name": "Main Branch",
    "location_type": "EMPLOYEE",
    "current_location": "Main Branch - Jane Doe",
    "days_assigned": 30
  }
]
```

#### Create Device
```
POST /api/devices/
Permission: HEAD_OFFICE

Body:
{
  "device_type": "Laptop",
  "brand": "Dell",
  "model": "XPS 13",
  "serial_number": "SN12345",
  "company_tag": "QR001",
  "purchase_date": "2024-01-01",
  "warranty_expiry": "2026-01-01",
  "location_type": "HEAD_OFFICE",
  "current_location": "Head Office",
  "condition_notes": "New condition"
}

Response: Device object with status = AVAILABLE
```

---

### 5. DEVICE ASSIGNMENTS

#### List Assignments
```
GET /api/assignments/
Permission: Authenticated

Query Parameters:
- employee: Filter by employee ID
- branch: Filter by branch ID
- returned_date: Filter by returned status (isnull=true for active)
- search: Search by device tag or employee name
- page: Page number

Response: [
  {
    "id": 1,
    "device": 1,
    "device_info": { ... },
    "employee": 1,
    "employee_name": "Jane Doe",
    "branch": 1,
    "branch_name": "Main Branch",
    "assigned_by": 1,
    "assigned_by_username": "admin",
    "received_by": null,
    "received_by_username": null,
    "assigned_date": "2024-01-15T10:00:00Z",
    "returned_date": null,
    "condition_on_issue": "Good",
    "condition_on_return": null,
    "days_assigned": 20
  }
]
```

#### Assign Device to Employee
```
POST /api/assignments/
Permission: HEAD_OFFICE

Body:
{
  "device_id": 1,
  "employee_id": 1,
  "condition_on_issue": "Good condition"
}

Response: Assignment object

Business Rules:
- Device must not already be assigned
- Device must not be IN_REPAIR, MISSING, or RETIRED
- Updates device status to ASSIGNED
- Creates audit log entry
```

#### Return Device
```
POST /api/assignments/{id}/return_device/
Permission: HEAD_OFFICE

Body:
{
  "condition_on_return": "Minor scratches"
}

Response: Updated assignment object

Business Rules:
- Sets returned_date to current time
- Updates device status to AVAILABLE
- Clears assignment from device
- Creates audit log entry
```

---

### 6. REPAIR REQUESTS

#### List Repair Requests
```
GET /api/repair-requests/
Permission: Authenticated

Query Parameters:
- status: Filter by status (PENDING, APPROVED, REJECTED, COMPLETED)
- priority: Filter by priority
- employee: Filter by employee ID
- search: Search by device tag or description
- page: Page number

Response: [
  {
    "id": 1,
    "device_info": {
      "id": 1,
      "company_tag": "QR001",
      "device_type": "Laptop"
    },
    "employee_name": "Jane Doe",
    "issue_description": "Screen flickering",
    "priority": "HIGH",
    "status": "PENDING",
    "request_date": "2024-01-20T10:00:00Z"
  }
]
```

#### Create Repair Request (Employee)
```
POST /api/repair-requests/
Permission: EMPLOYEE

Body:
{
  "device_id": 1,
  "issue_description": "Screen flickering",
  "priority": "HIGH"
}

Response: Repair request object with status = PENDING

Business Rules:
- Employee can only request repair for assigned devices
- Device must be ASSIGNED or IN_REPAIR
- Creates audit log entry
```

#### Approve Repair Request
```
POST /api/repair-requests/{id}/approve/
Permission: HEAD_OFFICE

Response: Updated repair request with status = APPROVED

Business Rules:
- Device status changes to IN_REPAIR
- Creates audit log entry
```

#### Reject Repair Request
```
POST /api/repair-requests/{id}/reject/
Permission: HEAD_OFFICE

Response: Updated repair request with status = REJECTED

Business Rules:
- Device status remains unchanged
- Creates audit log entry
```

---

### 7. REPAIR LOGS

#### List Repair Logs
```
GET /api/repair-logs/
Permission: Authenticated

Query Parameters:
- search: Search by device tag or technician name
- page: Page number

Response: [
  {
    "id": 1,
    "repair_request": 1,
    "repair_request_info": { ... },
    "technician": 2,
    "technician_username": "tech_user",
    "notes": "Replaced screen",
    "parts_used": "LCD Screen - model X",
    "start_date": "2024-01-21T10:00:00Z",
    "completed_date": null
  }
]
```

#### Complete Repair
```
POST /api/repair-logs/{id}/update_repair/
Permission: TECHNICIAN

Body:
{
  "notes": "Replaced screen and tested",
  "parts_used": "LCD Screen - model X, Thermal paste"
}

Response: Updated repair log with completed_date

Business Rules:
- Repair request must be APPROVED
- Sets completed_date to current time
- Updates repair request status to COMPLETED
- Device status changes back to ASSIGNED
- Creates audit log entry
```

---

### 8. INVENTORY SESSIONS

#### List Inventory Sessions
```
GET /api/inventory-sessions/
Permission: Authenticated

Query Parameters:
- branch: Filter by branch ID
- page: Page number

Response: [
  {
    "id": 1,
    "branch": 1,
    "branch_name": "Main Branch",
    "start_date": "2024-01-25T10:00:00Z",
    "end_date": null,
    "created_by": 1,
    "created_by_username": "admin",
    "approved_by_branch": false,
    "approved_by_head_office": false
  }
]
```

#### Create Inventory Session
```
POST /api/inventory-sessions/
Permission: HEAD_OFFICE

Body:
{
  "branch_id": 1
}

Response: Inventory session object

Business Rules:
- Session created for specific branch
- Auto-loads all devices assigned to branch
- Creates audit log entry
```

---

### 9. INVENTORY ITEMS

#### List Inventory Items
```
GET /api/inventory-items/
Permission: Authenticated

Query Parameters:
- session: Filter by session ID
- status: Filter by status (VERIFIED, MISSING)
- search: Search by device tag
- page: Page number

Response: [
  {
    "id": 1,
    "session": 1,
    "device": 1,
    "device_info": { ... },
    "status": "VERIFIED",
    "comment": "Device found and working"
  }
]
```

#### Mark Item as Verified
```
POST /api/inventory-items/{id}/mark_verified/
Permission: BRANCH_MANAGER

Body:
{
  "comment": "Device found and verified working"
}

Response: Updated inventory item

Business Rules:
- Updates status to VERIFIED
- Creates audit log entry
```

#### Mark Item as Missing
```
POST /api/inventory-items/{id}/mark_missing/
Permission: BRANCH_MANAGER

Body:
{
  "comment": "Device not found in inventory"
}

Response: Updated inventory item

Business Rules:
- Updates status to MISSING
- Updates device status to MISSING
- Creates audit log entry
```

---

### 10. NOTIFICATIONS

#### List My Notifications
```
GET /api/notifications/
Permission: Authenticated

Returns only current user's notifications

Query Parameters:
- page: Page number

Response: [
  {
    "id": 1,
    "user": 1,
    "message": "Device XPS-001 is pending return due to employee exit.",
    "is_read": false,
    "created_at": "2024-01-26T10:00:00Z"
  }
]
```

#### Mark Notification as Read
```
POST /api/notifications/{id}/mark_as_read/
Permission: Authenticated

Response: Updated notification with is_read = true
```

---

### 11. AUDIT LOGS

#### List Audit Logs
```
GET /api/audit-logs/
Permission: HEAD_OFFICE

Query Parameters:
- action: Filter by action type
- model_name: Filter by model name
- search: Search by action or details
- page: Page number

Response: [
  {
    "id": 1,
    "user": 1,
    "user_username": "admin",
    "action": "DEVICE_ASSIGNED",
    "model_name": "Device",
    "object_id": 1,
    "timestamp": "2024-01-15T10:00:00Z",
    "details": "Assigned to Jane Doe"
  }
]
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Device is already assigned to someone",
  "detail": "Detailed error message"
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "Only Head Office staff can access this resource."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 500 Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Business Logic Implementation

### Device Assignment Flow
1. HEAD_OFFICE creates assignment via POST /api/assignments/
2. System validates device is available
3. Device status changes to ASSIGNED
4. Audit log created automatically

### Repair Request Flow
1. EMPLOYEE creates repair request
2. HEAD_OFFICE approves/rejects
3. On approval, device status changes to IN_REPAIR
4. TECHNICIAN completes repair and updates logs
5. Device returns to ASSIGNED status

### Employee Exit Automation
1. HEAD_OFFICE marks employee as EXITED
2. System finds all active assignments
3. Device statuses change to PENDING_RETURN
4. Branch manager receives notification
5. Audit logs created

### Inventory Management
1. HEAD_OFFICE creates inventory session for branch
2. System auto-loads devices for verification
3. BRANCH_MANAGER marks items as VERIFIED or MISSING
4. Missing devices update to MISSING status
5. Audit logs track all changes

---

## Pagination

All list endpoints support pagination with `page` parameter (1-indexed).

Default page size: **20 items**

```
GET /api/devices/?page=2

Response:
{
  "count": 150,
  "next": "http://localhost:8000/api/devices/?page=3",
  "previous": "http://localhost:8000/api/devices/?page=1",
  "results": [ ... ]
}
```

---

## Filtering & Search

### Common Query Parameters

**Search:**
```
GET /api/devices/?search=QR001
GET /api/employees/?search=Jane
```

**Filtering:**
```
GET /api/devices/?status=ASSIGNED&device_type=Laptop
GET /api/employees/?branch=1&status=ACTIVE
```

**Ordering:**
```
GET /api/devices/?ordering=-purchase_date
GET /api/devices/?ordering=status
```

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request successful |
| 201 | Created - Resource successfully created |
| 204 | No Content - Successful but no content |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Permission denied |
| 404 | Not Found - Resource not found |
| 500 | Server Error - Internal error |

---

## Example Workflows

### Workflow 1: Device Assignment
```bash
# 1. Get available devices
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/devices/?status=AVAILABLE

# 2. Assign device to employee
curl -X POST -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": 1,
    "employee_id": 2,
    "condition_on_issue": "Good"
  }' \
  http://localhost:8000/api/assignments/

# 3. Track assignment
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/assignments/1/
```

### Workflow 2: Device Repair
```bash
# 1. Employee requests repair
curl -X POST -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": 1,
    "issue_description": "Screen issue",
    "priority": "HIGH"
  }' \
  http://localhost:8000/api/repair-requests/

# 2. HEAD_OFFICE approves
curl -X POST -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/repair-requests/1/approve/

# 3. Technician completes repair
curl -X POST -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Replaced screen",
    "parts_used": "LCD Screen"
  }' \
  http://localhost:8000/api/repair-logs/1/update_repair/
```

---

## Testing the API

### Quick Test with curl

```bash
# 1. Get token
TOKEN=$(curl -X POST -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  http://localhost:8000/api/auth/token/ | jq '.access')

# 2. Test authenticated endpoint
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/devices/
```

### Using Postman
1. Import API endpoints as Postman collection
2. Set `{{token}}` variable from token endpoint
3. Use Bearer token in Authorization header

---

## Rate Limiting (Future)

Rate limiting can be implemented using `djangorestframework-api-key` or similar packages.

---

## Version

API Version: **1.0**
Last Updated: January 2024

---

## Support

For issues or questions, contact the development team.
