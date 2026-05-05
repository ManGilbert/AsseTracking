# Device Management System (DMS) API

A production-ready Django REST Framework API for managing device lifecycle, employee management, device assignments, repairs, and inventory tracking with comprehensive role-based access control.

## Features

✅ **Complete Device Management**
- Track device lifecycle (Available, Assigned, In Repair, Missing, Retired)
- Store device details (serial number, company tag, warranty info)
- Location tracking (Head Office, Branch, Employee)

✅ **Employee Management**
- Employee profiles with department assignment
- Status tracking (Active, Inactive, Exited)
- Automated device return workflow on exit

✅ **Device Assignment System**
- HEAD_OFFICE controlled assignments
- Track assignment history with conditions
- Easy device returns with return workflow

✅ **Repair Workflow**
- Employees request repairs
- HEAD_OFFICE approves/rejects requests
- Technicians complete repairs with logs
- Automatic device status updates

✅ **Inventory Management**
- Branch-based inventory sessions
- Auto-load devices for verification
- Track verified and missing devices
- Automatic missing device status updates

✅ **Role-Based Access Control**
- HEAD_OFFICE: Full access (admin)
- BRANCH_MANAGER: Inventory verification and branch operations
- TECHNICIAN: Repair operations
- EMPLOYEE: Device requests and self-service

✅ **Audit Logging**
- Automatic audit trail for all actions
- Track user, action, timestamp, and details
- Searchable audit logs (HEAD_OFFICE only)

✅ **Notifications**
- Automated notifications for device returns
- Branch manager notifications on employee exit
- User notification management

✅ **API Features**
- JWT authentication with token refresh
- Pagination (20 items per page)
- Filtering, search, and ordering
- Comprehensive error handling
- RESTful endpoints

---

## Quick Start

### Prerequisites

- Python 3.8+
- Django 6.0.4
- Django REST Framework
- PostgreSQL (recommended for production) or SQLite (development)

### Installation

1. **Clone the repository**
```bash
cd "d:\Django rest framework\AsseTracking"
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/Scripts/activate  # Windows
# or
source venv/bin/activate  # macOS/Linux
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Apply migrations**
```bash
python manage.py migrate
```

5. **Create superuser**
```bash
python manage.py createsuperuser
# Username: admin
# Email: admin@example.com
# Password: (set strong password)
```

6. **Run development server**
```bash
python manage.py runserver
```

The API will be available at: `http://localhost:8000/api/`

---

## Project Structure

```
AsseTracking/
├── App/
│   ├── models.py              # Database models
│   ├── serializers.py         # DRF serializers
│   ├── views.py               # ViewSets with business logic
│   ├── permissions.py         # Custom permission classes
│   ├── services.py            # Business logic services
│   ├── signals.py             # Django signals for audit logging
│   ├── urls.py                # API URL routing
│   ├── apps.py                # App configuration
│   └── migrations/
│
├── AsseTracking/
│   ├── settings.py            # Django settings
│   ├── urls.py                # Project URL configuration
│   ├── wsgi.py                # WSGI entry point
│   └── asgi.py                # ASGI entry point
│
├── API_DOCUMENTATION.md       # Complete API documentation
├── README.md                  # This file
├── manage.py                  # Django management script
└── db.sqlite3                 # Development database
```

---

## API Endpoints Overview

### Authentication
- `POST /api/auth/token/` - Get access token
- `POST /api/auth/token/refresh/` - Refresh access token

### Users
- `GET /api/users/` - List users (HEAD_OFFICE only)
- `POST /api/users/` - Create user (HEAD_OFFICE only)
- `GET /api/users/{id}/` - Get user details

### Branches
- `GET /api/branches/` - List branches
- `POST /api/branches/` - Create branch (HEAD_OFFICE only)
- `GET /api/branches/{id}/` - Get branch details

### Departments
- `GET /api/departments/` - List departments
- `POST /api/departments/` - Create department (HEAD_OFFICE only)

### Employees
- `GET /api/employees/` - List employees
- `POST /api/employees/` - Create employee (HEAD_OFFICE only)
- `POST /api/employees/{id}/set_exit_status/` - Mark employee as exited

### Devices
- `GET /api/devices/` - List devices (with filtering/search)
- `POST /api/devices/` - Create device (HEAD_OFFICE only)
- `GET /api/devices/{id}/` - Get device details

### Device Assignments
- `GET /api/assignments/` - List assignments
- `POST /api/assignments/` - Assign device (HEAD_OFFICE only)
- `POST /api/assignments/{id}/return_device/` - Return device

### Repair Requests
- `GET /api/repair-requests/` - List repair requests
- `POST /api/repair-requests/` - Create repair request (EMPLOYEE only)
- `POST /api/repair-requests/{id}/approve/` - Approve repair (HEAD_OFFICE only)
- `POST /api/repair-requests/{id}/reject/` - Reject repair (HEAD_OFFICE only)

### Repair Logs
- `GET /api/repair-logs/` - List repair logs
- `POST /api/repair-logs/{id}/update_repair/` - Complete repair (TECHNICIAN only)

### Inventory Sessions
- `GET /api/inventory-sessions/` - List inventory sessions
- `POST /api/inventory-sessions/` - Create session (HEAD_OFFICE only)

### Inventory Items
- `GET /api/inventory-items/` - List inventory items
- `POST /api/inventory-items/{id}/mark_verified/` - Mark verified (BRANCH_MANAGER only)
- `POST /api/inventory-items/{id}/mark_missing/` - Mark missing (BRANCH_MANAGER only)

### Notifications
- `GET /api/notifications/` - List my notifications
- `POST /api/notifications/{id}/mark_as_read/` - Mark as read

### Audit Logs
- `GET /api/audit-logs/` - List audit logs (HEAD_OFFICE only)

---

## Authentication

### Get Token
```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_password"
  }'
```

### Use Token in Requests
```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:8000/api/devices/
```

---

## User Roles

### HEAD_OFFICE (Admin)
- Full system access
- Create/manage users and devices
- Approve repairs and create inventory sessions
- View audit logs

### BRANCH_MANAGER
- Manage branch operations
- Verify inventory items
- View branch-specific data

### TECHNICIAN
- Update repair logs
- Complete repairs

### EMPLOYEE
- Request device repairs
- View assigned devices
- Create repair requests

---

## Database Models

### User
- Inherits from AbstractBaseUser
- Role-based (HEAD_OFFICE, BRANCH_MANAGER, TECHNICIAN, EMPLOYEE)
- Email and username unique

### Employee
- Links User with employee profile
- Department and branch assignment
- Status tracking (Active, Inactive, Exited)
- Hire and exit dates

### Device
- Device details and specifications
- Status tracking (7 possible states)
- Assignment tracking
- Location information
- Warranty tracking

### DeviceAssignment
- Track device-employee assignments
- Condition on issue/return
- Audit trail with assigned_by and received_by

### RepairRequest
- Issue description and priority
- Status workflow (Pending → Approved/Rejected → Completed)
- HEAD_OFFICE approval required

### RepairLog
- Technician notes and parts used
- Start and completion dates
- Linked to RepairRequest

### InventorySession
- Branch-specific inventory audits
- Start/end dates
- Approval workflow

### InventoryItem
- Items in inventory session
- Status (Verified/Missing)
- Comments

### AuditLog
- Complete audit trail
- User, action, timestamp, details
- Model-agnostic object tracking

### Notification
- User-specific notifications
- Read/unread status
- Timestamp tracking

---

## Business Logic Implementation

### Device Assignment Flow
```
1. HEAD_OFFICE creates assignment
2. System validates device is available
3. Device status → ASSIGNED
4. Device linked to employee and branch
5. Audit log created
```

### Repair Request Flow
```
1. EMPLOYEE creates repair request
2. Device must be ASSIGNED or IN_REPAIR
3. HEAD_OFFICE approves/rejects
4. On approval: Device status → IN_REPAIR
5. TECHNICIAN completes repair
6. Device status → ASSIGNED
7. Audit log tracks all changes
```

### Employee Exit Flow
```
1. HEAD_OFFICE marks employee as EXITED
2. System finds all active assignments
3. Device status → PENDING_RETURN
4. Branch manager receives notification
5. Audit logs created
```

### Inventory Management Flow
```
1. HEAD_OFFICE creates session for branch
2. System auto-loads devices
3. BRANCH_MANAGER verifies items
4. MISSING items → device status MISSING
5. Audit trail maintained
```

---

## Settings Configuration

Key settings in `AsseTracking/settings.py`:

```python
# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Pagination
'PAGE_SIZE': 20

# Filter backends
'DEFAULT_FILTER_BACKENDS': [
    'django_filters.rest_framework.DjangoFilterBackend',
    'rest_framework.filters.SearchFilter',
    'rest_framework.filters.OrderingFilter',
]

# Custom User Model
AUTH_USER_MODEL = 'App.User'
```

---

## Testing

### Quick Test
```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' | jq -r '.access')

# Test authenticated endpoint
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/devices/
```

### Using Postman
1. Import API collection from API_DOCUMENTATION.md
2. Set authorization header: `Bearer {{token}}`
3. Test endpoints

---

## Deployment Considerations

### Production Setup
1. Use PostgreSQL instead of SQLite
2. Set `DEBUG = False` in settings
3. Configure allowed hosts
4. Use environment variables for secrets
5. Set up CORS for frontend
6. Configure static files (WhiteNoise)
7. Use Gunicorn as WSGI server
8. Set up SSL/TLS certificates

### Environment Variables
```bash
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgresql://user:password@localhost/dbname
JWT_SECRET_KEY=your-jwt-secret
```

### Performance Optimization
- Use database indexing
- Implement caching
- Optimize queries with select_related/prefetch_related
- Use pagination (already implemented)
- Consider read replicas for large datasets

---

## Error Handling

All error responses follow standard HTTP status codes:

- `200 OK` - Successful GET/PATCH/PUT request
- `201 Created` - Successful POST request
- `204 No Content` - Successful DELETE request
- `400 Bad Request` - Validation error
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found
- `500 Server Error` - Internal server error

---

## Audit Logging

All actions are logged automatically:
- Device creation/updates
- Assignments and returns
- Repair requests and completions
- Inventory changes
- Employee exit

View audit logs at: `GET /api/audit-logs/` (HEAD_OFFICE only)

---

## Security Features

✅ **Authentication**
- JWT tokens with expiration
- Token refresh mechanism
- Secure password hashing

✅ **Authorization**
- Role-based access control
- Permission decorators on endpoints
- Object-level permissions

✅ **Data Protection**
- HTTPS support (production)
- CSRF protection
- SQL injection protection (ORM)

✅ **Validation**
- Input validation on all endpoints
- Business logic validation
- Constraint enforcement

---

## Troubleshooting

### Common Issues

**"No module named 'django_filters'"**
```bash
pip install django-filter
```

**"ModuleNotFoundError: No module named 'App'"**
```bash
# Make sure INSTALLED_APPS includes 'App'
# Check settings.py for correct configuration
```

**"Authentication credentials were not provided"**
```bash
# Add Authorization header to request
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/
```

**"Only Head Office staff can access this resource"**
```bash
# Use HEAD_OFFICE role user or check permissions
```

---

## API Documentation

Full API documentation including all endpoints, request/response examples, and workflows is available in [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

---

## Future Enhancements

- [ ] Real-time notifications (WebSockets)
- [ ] Device status analytics dashboard
- [ ] Scheduled maintenance tracking
- [ ] Device replacement recommendations
- [ ] Cost tracking and reporting
- [ ] Mobile app integration
- [ ] Multi-tenancy support
- [ ] Advanced reporting (PDF export)
- [ ] Device usage analytics
- [ ] Predictive maintenance

---

## Contributing

1. Create feature branch
2. Implement changes
3. Add tests
4. Submit pull request

---

## License

MIT License - See LICENSE file for details

---

## Support

For issues, questions, or feedback, contact the development team.

---

**Version:** 1.0
**Last Updated:** January 2024
**Author:** Development Team
