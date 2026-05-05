# Device Management System - Developer Guide

A comprehensive guide for developers working on the DMS API.

---

## 📋 Table of Contents

1. [Architecture](#architecture)
2. [Setup](#setup)
3. [Code Organization](#code-organization)
4. [Adding Features](#adding-features)
5. [Testing](#testing)
6. [Best Practices](#best-practices)
7. [Common Tasks](#common-tasks)
8. [Troubleshooting](#troubleshooting)

---

## 🏗️ Architecture

### Layered Architecture

```
┌─ Views Layer (API Endpoints)
│  ├─ Receives HTTP requests
│  ├─ Validates permissions
│  └─ Returns JSON responses
│
├─ Serializer Layer (Data Validation)
│  ├─ Validates input data
│  ├─ Transforms data for API
│  └─ Handles nested relationships
│
├─ Service Layer (Business Logic)
│  ├─ Implements business rules
│  ├─ Manages transactions
│  └─ Creates audit logs
│
└─ Model Layer (Data Persistence)
   ├─ Defines database schema
   ├─ Implements constraints
   └─ Manages relationships
```

### Request Flow

```
HTTP Request
    ↓
View (Permission Check)
    ↓
Serializer (Validation)
    ↓
Service (Business Logic)
    ↓
Model (Database)
    ↓
Audit Log (Signal)
    ↓
HTTP Response
```

---

## 🛠️ Setup

### Development Environment

```bash
# 1. Clone repository
cd "d:\Django rest framework\AsseTracking"

# 2. Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Create superuser
python manage.py createsuperuser

# 6. Start development server
python manage.py runserver

# Access at http://localhost:8000/api/
```

### Database Migrations

```bash
# Create new migration
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations

# Rollback migration
python manage.py migrate app_name 0001
```

---

## 📁 Code Organization

### File Structure

```
App/
├── models.py              # Database models (12 models)
├── serializers.py         # Serializers (14 classes)
├── views.py              # ViewSets (12 classes)
├── permissions.py        # Permissions (13 classes)
├── services.py           # Business logic (5 services)
├── signals.py            # Event handlers (3 signals)
├── urls.py               # URL routing
├── apps.py               # App configuration
├── admin.py              # Admin configuration
├── tests.py              # Unit tests
└── migrations/           # Database migrations
```

### Code Style

**Follow these conventions:**

- **Naming:** snake_case for functions, CamelCase for classes
- **Comments:** Use docstrings for all classes and methods
- **Imports:** Group standard, third-party, local imports
- **Line Length:** Maximum 100 characters
- **Indentation:** 4 spaces

**Example:**

```python
from django.db import models
from rest_framework import serializers

from .models import Device


class DeviceSerializer(serializers.ModelSerializer):
    """
    Serializer for Device model.
    
    Handles validation and transformation of device data.
    """
    
    class Meta:
        model = Device
        fields = ('id', 'serial_number', 'status')
```

---

## ➕ Adding Features

### Adding a New Endpoint

#### 1. Create Model
```python
# App/models.py
class NewModel(models.Model):
    """New model description."""
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
```

#### 2. Create Serializer
```python
# App/serializers.py
class NewModelSerializer(serializers.ModelSerializer):
    """Serializer for NewModel."""
    
    class Meta:
        model = NewModel
        fields = ('id', 'name', 'created_at')
        read_only_fields = ('id', 'created_at')
```

#### 3. Create ViewSet
```python
# App/views.py
class NewModelViewSet(viewsets.ModelViewSet):
    """API endpoint for new model."""
    
    queryset = NewModel.objects.all()
    serializer_class = NewModelSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    
    def get_permissions(self):
        if self.action == 'create':
            return [IsHeadOffice()]
        return [IsAuthenticated()]
```

#### 4. Register URL
```python
# App/urls.py
router.register(r'new-models', NewModelViewSet, basename='new-model')
```

#### 5. Create Migration
```bash
python manage.py makemigrations
python manage.py migrate
```

### Adding Permission

```python
# App/permissions.py
class CanManageNewModel(permissions.BasePermission):
    """Allow specific role to manage new model."""
    
    message = "Only authorized users can manage this resource."
    
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "REQUIRED_ROLE"
        )
```

### Adding Custom Action

```python
# App/views.py
class ExampleViewSet(viewsets.ModelViewSet):
    ...
    
    @action(detail=True, methods=['post'])
    def custom_action(self, request, pk=None):
        """
        Custom action on specific endpoint.
        
        POST /api/example/{id}/custom_action/
        """
        obj = self.get_object()
        
        # Business logic here
        
        serializer = self.get_serializer(obj)
        return Response(serializer.data)
```

### Adding Service Layer

```python
# App/services.py
class NewService:
    """Service for new feature."""
    
    @staticmethod
    def do_something(param1, param2):
        """
        Perform complex operation.
        
        Args:
            param1: First parameter
            param2: Second parameter
            
        Returns:
            Result object
        """
        # Implementation
        return result
```

---

## 🧪 Testing

### Writing Tests

```python
# App/tests.py
from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import Device
from .serializers import DeviceSerializer


class DeviceTestCase(TestCase):
    """Test cases for Device model."""
    
    def setUp(self):
        """Set up test data."""
        self.device = Device.objects.create(
            device_type='Laptop',
            serial_number='SN123',
            company_tag='QR001'
        )
    
    def test_device_creation(self):
        """Test device creation."""
        self.assertEqual(self.device.status, 'AVAILABLE')
        self.assertIsNotNone(self.device.id)


class DeviceAPITestCase(APITestCase):
    """Test cases for Device API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.device = Device.objects.create(
            device_type='Laptop',
            serial_number='SN123',
            company_tag='QR001'
        )
    
    def test_list_devices(self):
        """Test listing devices."""
        response = self.client.get('/api/devices/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
```

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific test module
python manage.py test App.tests

# Run specific test class
python manage.py test App.tests.DeviceTestCase

# Run specific test method
python manage.py test App.tests.DeviceTestCase.test_device_creation

# Run with verbose output
python manage.py test --verbosity=2

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

---

## 💡 Best Practices

### 1. Business Logic in Services

❌ **Don't do this in views:**
```python
def create(self, request):
    # Complex business logic in view
    device.status = 'ASSIGNED'
    employee.devices.add(device)
    device.save()
    return Response(...)
```

✅ **Do this instead:**
```python
# App/services.py
class DeviceAssignmentService:
    @staticmethod
    def assign_device(device, employee):
        # All logic in service
        pass

# App/views.py
def create(self, request):
    DeviceAssignmentService.assign_device(device, employee)
    return Response(...)
```

### 2. Use Serializers for Validation

❌ **Don't do this:**
```python
if not device:
    return Response({'error': 'Device not found'}, status=404)
```

✅ **Do this instead:**
```python
class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ('id', 'serial_number')
    
    def validate_serial_number(self, value):
        if not value:
            raise serializers.ValidationError("Serial number required")
        return value
```

### 3. Use Permissions Classes

❌ **Don't do this:**
```python
def update(self, request, pk=None):
    if request.user.role != 'HEAD_OFFICE':
        return Response({'error': 'Permission denied'}, status=403)
    # ...
```

✅ **Do this instead:**
```python
from .permissions import IsHeadOffice

class DeviceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsHeadOffice]
    # ...
```

### 4. Use Transactions for Atomic Operations

```python
from django.db import transaction

@transaction.atomic
def critical_operation(self):
    """Ensures all-or-nothing execution."""
    # Multiple operations that should succeed or fail together
    model1.save()
    model2.save()
    model3.delete()
```

### 5. Meaningful Error Messages

```python
# Good error messages
raise ValueError("Device is already assigned to another employee")
raise ValueError(f"Device {device.company_tag} is in repair status")

# Bad error messages
raise ValueError("Invalid device")
raise ValueError("Error")
```

### 6. Comprehensive Docstrings

```python
def assign_device(device_id, employee_id, assigned_by_user):
    """
    Assign device to employee.
    
    Args:
        device_id (int): ID of device to assign
        employee_id (int): ID of employee to assign to
        assigned_by_user (User): User performing assignment
    
    Returns:
        DeviceAssignment: Created assignment object
    
    Raises:
        ValueError: If device already assigned or invalid state
        Device.DoesNotExist: If device not found
        Employee.DoesNotExist: If employee not found
    
    Example:
        >>> assignment = assign_device(1, 2, user)
        >>> print(assignment.device.company_tag)
        'QR001'
    """
```

---

## 🔄 Common Tasks

### Adding a New Role

1. **Update Model:**
```python
# App/models.py
class User(AbstractBaseUser):
    ROLE_CHOICES = [
        ('HEAD_OFFICE', 'Head Office'),
        ('NEW_ROLE', 'New Role'),  # Add here
    ]
```

2. **Create Permission:**
```python
# App/permissions.py
class IsNewRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == "NEW_ROLE"
```

3. **Use in ViewSet:**
```python
# App/views.py
permission_classes = [IsNewRole]
```

### Adding Filtering

```python
# App/views.py
class DeviceViewSet(viewsets.ModelViewSet):
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ['status', 'branch']
    search_fields = ['serial_number', 'company_tag']
    ordering_fields = ['purchase_date']
    ordering = ['-purchase_date']
```

### Adding Audit Logging

```python
# App/services.py
AuditLog.objects.create(
    user=request.user,
    action='DEVICE_ASSIGNED',
    model_name='Device',
    object_id=device.id,
    details=f'Assigned to {employee.full_name}'
)
```

### Adding Pagination

Already configured globally, customize per ViewSet:
```python
# App/views.py
from rest_framework.pagination import PageNumberPagination

class CustomPagination(PageNumberPagination):
    page_size = 50

class ExampleViewSet(viewsets.ModelViewSet):
    pagination_class = CustomPagination
```

---

## 🐛 Troubleshooting

### Common Issues

**Issue: "Module not found" error**
```bash
# Solution: Ensure all imports are correct
# Check INSTALLED_APPS in settings.py
# Verify file names match imports
```

**Issue: Migration conflicts**
```bash
# Solution: Merge or squash migrations
python manage.py migrate --fake
python manage.py squashmigrations
```

**Issue: Permission denied on all endpoints**
```bash
# Check:
# 1. User is authenticated (has valid token)
# 2. User has correct role
# 3. Correct permission classes are applied
```

**Issue: Serializer validation failing**
```bash
# Debug:
if not serializer.is_valid():
    print(serializer.errors)  # Shows validation errors
```

**Issue: N+1 Query Problem**
```python
# Solution: Use select_related/prefetch_related
queryset = Device.objects.select_related('assigned_employee')
queryset = Device.objects.prefetch_related('assignments')
```

---

## 📚 Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django REST Framework Filters](https://django-filter.readthedocs.io/)
- [Postman Collection](https://www.postman.com/)

---

## 📝 Checklist for New Features

- [ ] Models created and migrated
- [ ] Serializers implemented with validation
- [ ] ViewSets created with proper permissions
- [ ] URLs registered in urls.py
- [ ] Permissions classes defined if needed
- [ ] Service layer implemented
- [ ] Audit logging added
- [ ] Tests written
- [ ] API documentation updated
- [ ] Error handling added
- [ ] Docstrings completed

---

## 🚀 Deployment Checklist

- [ ] DEBUG = False
- [ ] SECRET_KEY changed
- [ ] ALLOWED_HOSTS configured
- [ ] Database migrated
- [ ] Environment variables set
- [ ] Static files collected
- [ ] CORS configured if needed
- [ ] HTTPS enabled
- [ ] Logging configured
- [ ] Backups configured
- [ ] Monitoring set up

---

**Version:** 1.0
**Last Updated:** January 2024
