# 🎯 HEAD OFFICE DASHBOARD - QUICK START GUIDE

## 📍 Dashboard Access

All Head Office modules are accessible from the main dashboard after login with HEAD_OFFICE role:

```
http://localhost:8000/dashboard/head-office/
```

## 🗂️ Module URLs

| Module | URL | Icon |
|--------|-----|------|
| Dashboard | `/dashboard/head-office/` | 📊 |
| Employee Management | `/head-office/employees/` | 👥 |
| Branch Management | `/head-office/branches/` | 🗺️ |
| Device Management | `/head-office/devices/` | 💻 |
| Device Assignments | `/head-office/assignments/` | ➡️ |
| Repair Management | `/head-office/repairs/` | 🔧 |
| Inventory Management | `/head-office/inventory/` | 📦 |
| Audit Logs | `/head-office/audit-logs/` | 📜 |

## 🔌 API ENDPOINTS

### Base URL
```
http://localhost:8000/api/
```

### Users
```
GET    /api/users/                    - List all users (HEAD_OFFICE only)
POST   /api/users/                    - Create user (HEAD_OFFICE only)
GET    /api/users/{id}/               - Get user details
PATCH  /api/users/{id}/               - Update user
```

### Employees
```
GET    /api/employees/                - List employees
POST   /api/employees/                - Create employee (HEAD_OFFICE only)
GET    /api/employees/{id}/           - Get employee details
PATCH  /api/employees/{id}/           - Update employee (HEAD_OFFICE only)
POST   /api/employees/{id}/set_exit_status/  - Mark as exited
```

### Branches
```
GET    /api/branches/                 - List branches
POST   /api/branches/                 - Create branch (HEAD_OFFICE only)
GET    /api/branches/{id}/            - Get branch details
PATCH  /api/branches/{id}/            - Update branch (HEAD_OFFICE only)
DELETE /api/branches/{id}/            - Delete branch (HEAD_OFFICE only)
```

### Departments
```
GET    /api/departments/              - List departments
POST   /api/departments/              - Create department (HEAD_OFFICE only)
GET    /api/departments/{id}/         - Get department details
DELETE /api/departments/{id}/         - Delete department (HEAD_OFFICE only)
```

### Devices
```
GET    /api/devices/                  - List devices (supports filtering)
POST   /api/devices/                  - Register device (HEAD_OFFICE only)
GET    /api/devices/{id}/             - Get device details
PATCH  /api/devices/{id}/             - Update device (HEAD_OFFICE only)
DELETE /api/devices/{id}/             - Delete device (HEAD_OFFICE only)

Query Parameters:
  - status=AVAILABLE|ASSIGNED|IN_REPAIR|MISSING|RETIRED|PENDING_RETURN
  - assigned_branch={branch_id}
  - device_type={type}
  - search={query}
```

### Device Assignments
```
GET    /api/assignments/              - List assignments
POST   /api/assignments/              - Create assignment (HEAD_OFFICE only)
GET    /api/assignments/{id}/         - Get assignment details
POST   /api/assignments/{id}/return_device/  - Return device (HEAD_OFFICE only)

Query Parameters:
  - returned_date__isnull=True       - Active only
  - returned_date__isnull=False      - Returned only
```

### Repair Requests
```
GET    /api/repair-requests/          - List repair requests
POST   /api/repair-requests/          - Create repair (EMPLOYEE)
GET    /api/repair-requests/{id}/     - Get repair details
POST   /api/repair-requests/{id}/approve/    - Approve (HEAD_OFFICE only)
POST   /api/repair-requests/{id}/reject/     - Reject (HEAD_OFFICE only)

Status Values: PENDING, APPROVED, REJECTED, IN_PROGRESS, COMPLETED
Priority Values: HIGH, NORMAL, LOW
```

### Repair Logs
```
GET    /api/repair-logs/              - List repair logs
POST   /api/repair-logs/{id}/update_repair/  - Complete repair (TECHNICIAN)
```

### Inventory Sessions
```
GET    /api/inventory-sessions/       - List sessions
POST   /api/inventory-sessions/       - Create session (HEAD_OFFICE only)
GET    /api/inventory-sessions/{id}/  - Get session details

Query Parameters:
  - branch={branch_id}
```

### Inventory Items
```
GET    /api/inventory-items/          - List items
POST   /api/inventory-items/{id}/mark_verified/   - Mark verified
POST   /api/inventory-items/{id}/mark_missing/    - Mark missing
```

### Audit Logs
```
GET    /api/audit-logs/               - List activities (HEAD_OFFICE only)
GET    /api/audit-logs/{id}/          - Get log details (HEAD_OFFICE only)

Query Parameters:
  - action={ACTION_NAME}
  - model_name={MODEL_NAME}
  - search={query}
```

## 📊 Dashboard Statistics

The dashboard automatically displays:

- **Device Metrics**: Total, Assigned, Available, In Repair, Missing
- **Employee Metrics**: Total, Active, Inactive, Exited
- **Branch Metrics**: Total branches
- **Repair Metrics**: Pending, Approved, Completed
- **Charts**: Device status distribution, Device types, Devices per branch
- **Activities**: Recent audit logs and repair requests

## 🔐 Authentication

### Login
```bash
POST /login/
Body:
{
  "username": "your_username",
  "password": "your_password"
}
```

### API Authentication (JWT)
```bash
POST /api/token/
Body:
{
  "username": "your_username",
  "password": "your_password"
}

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLC...",
  "refresh": "eyJ0eXAiOiJKV1QiLC..."
}

# Use in headers:
Authorization: Bearer {access_token}
```

## 🎯 KEY WORKFLOWS

### 1. Hire New Employee
```
1. Create User (role: EMPLOYEE) → /api/users/
2. Create Employee Profile → /api/employees/
3. Link User to Employee
4. Assign to Branch & Department
5. Assign device(s) → /api/assignments/
```

### 2. Assign Device
```
1. Register Device → /api/devices/ (status: AVAILABLE)
2. Go to Device Assignments module
3. Select device and employee
4. Submit → Device status becomes ASSIGNED
5. Audit log created automatically
```

### 3. Request & Approve Repair
```
1. Employee creates repair request → /api/repair-requests/
2. Head Office reviews pending repairs
3. Approve → Device status: IN_REPAIR
4. Technician completes repair → /api/repair-logs/{id}/update_repair/
5. Device status: REPAIRED → AVAILABLE
```

### 4. Employee Exit Process
```
1. Go to Employee Management
2. Click employee's "Mark as Exited" button
3. System automatically:
   - Sets employee status to EXITED
   - Marks all active devices to PENDING_RETURN
   - Creates audit log
4. Track returned/missing devices
```

### 5. Inventory Verification
```
1. Create inventory session → /api/inventory-sessions/
2. Select branch and dates
3. Go to branch and verify devices
4. Mark as VERIFIED or MISSING
5. Head Office approves
```

## ⚙️ FILTERS & SEARCH

### Employee Filtering
- By Status: ACTIVE, INACTIVE, EXITED
- By Branch: Select from dropdown
- Search: Name, position

### Device Filtering
- By Status: All status values
- By Branch: Assigned branch
- By Type: Device type
- Search: Tag, serial number, model

### Assignment Filtering
- Active: `returned_date__isnull=True`
- Returned: `returned_date__isnull=False`
- Search: Device tag, employee name

### Repair Filtering
- By Status: Workflow stage
- By Priority: HIGH, NORMAL
- By Employee
- Search: Device tag, issue description

## 📈 DASHBOARD CHARTS

### Device Status Chart
Pie/Doughnut chart showing breakdown:
- Available (Green)
- Assigned (Cyan)
- Pending Return (Yellow)
- In Repair (Orange)
- Repaired (Purple)
- Missing (Red)
- Retired (Gray)

### Device Type Chart
Horizontal bar chart showing count by device type

### Devices per Branch
Vertical bar chart showing device distribution

## 🔔 ROLE PERMISSIONS

### HEAD_OFFICE Can:
✅ Create users of all roles
✅ Create employees and link to users
✅ Register and manage devices
✅ Approve device assignments
✅ Return devices
✅ Approve/Reject repairs
✅ Create inventory sessions
✅ View audit logs
✅ Mark employees as exited
✅ Create branches and departments

### BRANCH_MANAGER Can:
✅ View branch-specific data
✅ Manage local employees
✅ Request repairs
✅ Verify inventory items

### TECHNICIAN Can:
✅ View assigned repairs
✅ Complete repairs
✅ Update repair logs

### EMPLOYEE Can:
✅ View assigned devices
✅ Request repairs for devices
✅ View notifications

## 🐛 TROUBLESHOOTING

### Authentication Issues
- Ensure user role is HEAD_OFFICE
- Check CSRF token in cookies
- Verify JWT token not expired

### API Errors
- 403 Forbidden: Check user role and permissions
- 404 Not Found: Verify resource ID exists
- 400 Bad Request: Check request body format

### Template Issues
- Clear browser cache
- Ensure all CSS files load (check browser console)
- Verify Bootstrap and Chart.js CDN available

## 📱 RESPONSIVE DESIGN

All templates are fully responsive:
- Desktop: Full layout with sidebars
- Tablet: Stacked columns
- Mobile: Single column, hamburger menus

## 💾 DATA PERSISTENCE

All changes are immediately persisted:
- Database transactions atomic
- Audit logs created on every change
- No manual save button required
- Real-time updates via API

## 🚀 PERFORMANCE TIPS

1. Use filters to reduce data loaded
2. Search before scrolling large tables
3. Archive old inventory sessions
4. Regular database maintenance

---

**Status**: ✅ Production Ready
**Last Updated**: 2026-05-06
**Version**: 1.0
