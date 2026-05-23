from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


# =========================
# USER MANAGER
# =========================
class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, role='EMPLOYEE'):
        if not email:
            raise ValueError("User must have an email")

        email = self.normalize_email(email)

        user = self.model(
            username=username,
            email=email,
            role=role
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password):
        user = self.create_user(username, email, password, role='HEAD_OFFICE')
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


# =========================
# USER
# =========================
class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('HEAD_OFFICE', 'Head Office'),
        ('BRANCH_MANAGER', 'Branch Manager'),
        ('TECHNICIAN', 'Technician'),
        ('EMPLOYEE', 'Employee'),
    ]

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='EMPLOYEE')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)

    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_deleted_records",
    )
    deletion_reason = models.TextField(blank=True)

    class Meta:
        abstract = True

    def soft_delete(self, user=None, reason=""):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.deletion_reason = reason or ""
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "deletion_reason"])

    def restore(self, user=None):
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.deletion_reason = ""
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "deletion_reason"])


# =========================
# BRANCH
# =========================
class Branch(SoftDeleteModel):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)

    manager = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_branches'
    )

    def __str__(self):
        return self.name


# =========================
# DEPARTMENT
# =========================
class Department(SoftDeleteModel):
    name = models.CharField(max_length=255)

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='departments'
    )

    def __str__(self):
        return f"{self.name} ({self.branch})"


# =========================
# EMPLOYEE
# =========================
class Employee(SoftDeleteModel):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('EXITED', 'Exited'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)

    employee_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=255)
    position = models.CharField(max_length=255)

    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, related_name='employees')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')

    hire_date = models.DateField(null=True, blank=True)
    exit_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.full_name


# =========================
# DEVICE
# =========================
class Device(SoftDeleteModel):
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('ASSIGNED', 'Assigned'),
        ('PENDING_RETURN', 'Pending Return'),
        ('IN_REPAIR', 'In Repair'),
        ('COMPLETED', 'Completed'),
        ('REPAIRED', 'Repaired'),
        ('MISSING', 'Missing'),
        ('RETIRED', 'Retired'),
        ('DECOMMISSIONED', 'Decommissioned'),
    ]

    LOCATION_CHOICES = [
        ('HEAD_OFFICE', 'Head Office'),
        ('BRANCH', 'Branch'),
        ('EMPLOYEE', 'Employee'),
        ('TECHNICIAN', 'Head Office / Technician'),
    ]

    device_type = models.CharField(max_length=50)
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    serial_number = models.CharField(max_length=100, unique=True)
    company_tag = models.CharField(max_length=100, unique=True)  # QR / Barcode

    purchase_date = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')

    assigned_employee = models.ForeignKey('Employee', null=True, blank=True, on_delete=models.SET_NULL)
    assigned_branch = models.ForeignKey('Branch', null=True, blank=True, on_delete=models.SET_NULL)

    location_type = models.CharField(max_length=20, choices=LOCATION_CHOICES, default='HEAD_OFFICE')
    current_location = models.CharField(max_length=255, default="Head Office")

    condition_notes = models.TextField(blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    decommissioned_at = models.DateTimeField(null=True, blank=True)
    decommissioned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="decommissioned_devices",
    )
    decommission_reason = models.CharField(max_length=255, blank=True)
    decommission_notes = models.TextField(blank=True)
    previous_status_before_decommission = models.CharField(max_length=20, blank=True)
    last_location_before_decommission = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.device_type} - {self.company_tag}"

    @property
    def decommissioned_days_ago(self):
        if not self.decommissioned_at:
            return None
        return max(0, (timezone.now() - self.decommissioned_at).days)

    @property
    def decommission_days_remaining(self):
        if not self.decommissioned_at:
            return None
        remaining = 15 - self.decommissioned_days_ago
        return remaining if remaining >= 0 else 0

    @property
    def is_decommission_location_hidden(self):
        return self.status == 'DECOMMISSIONED' and self.decommissioned_at and self.decommissioned_days_ago >= 15

    @property
    def effective_current_location(self):
        if self.is_decommission_location_hidden:
            return None
        return self.current_location

    def has_activity_history(self):
        return (
            self.assignments.exists()
            or RepairRequest.objects.filter(device=self).exists()
            or InventoryItem.objects.filter(device=self).exists()
        )

    def delete(self, *args, **kwargs):
        if self.pk and self.has_activity_history():
            raise ValidationError(
                "Device cannot be deleted because it has related activity/history."
            )
        return super().delete(*args, **kwargs)


# =========================
# DEVICE ASSIGNMENT
# =========================
class DeviceAssignment(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='assignments')

    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True)

    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_devices')
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    assigned_date = models.DateTimeField(auto_now_add=True)
    returned_date = models.DateTimeField(null=True, blank=True)

    condition_on_issue = models.TextField(blank=True)
    condition_on_return = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['device'],
                condition=models.Q(returned_date__isnull=True),
                name='unique_active_assignment'
            )
        ]

    def __str__(self):
        return f"{self.device} -> {self.employee}"


# =========================
# REPAIR REQUEST
# =========================
class RepairRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    ]

    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

    issue_description = models.TextField()
    priority = models.CharField(max_length=20, default='NORMAL')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    request_date = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.device} - {self.status}"


# =========================
# REPAIR LOG
# =========================
class RepairLog(models.Model):
    repair_request = models.OneToOneField(RepairRequest, on_delete=models.CASCADE)

    technician = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    notes = models.TextField()
    parts_used = models.TextField(blank=True)

    start_date = models.DateTimeField(default=timezone.now)
    completed_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Repair - {self.repair_request.device}"


# =========================
# INVENTORY SESSION
# =========================
class InventorySession(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inventorysession_deleted_records",
    )
    deletion_reason = models.TextField(blank=True)

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)

    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    approved_by_branch = models.BooleanField(default=False)
    approved_by_head_office = models.BooleanField(default=False)

    @property
    def is_active(self):
        if not self.end_date:
            return True
        return timezone.now() < self.end_date

    @property
    def is_closed(self):
        if not self.end_date:
            return False
        return timezone.now() >= self.end_date

    def __str__(self):
        return f"{self.branch} Inventory"

    def soft_delete(self, user=None, reason=""):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.deletion_reason = reason or ""
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "deletion_reason"])

    def restore(self, user=None):
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.deletion_reason = ""
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "deletion_reason"])


# =========================
# INVENTORY ITEM
# =========================
class InventoryItem(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('VERIFIED', 'Verified'),
        ('MISSING', 'Missing'),
        ('EXTRA', 'Extra'),
        ('IN_REPAIR', 'In Repair'),
        ('RETURNED_HEAD_OFFICE', 'Returned to Head Office'),
    ]

    session = models.ForeignKey(InventorySession, on_delete=models.CASCADE, related_name='items')
    device = models.ForeignKey(Device, on_delete=models.CASCADE)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ['session', 'device']


# =========================
# NOTIFICATION
# =========================
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    message = models.TextField()
    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user}"


# =========================
# AUDIT LOG
# =========================
class AuditLog(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    action = models.CharField(max_length=255)
    model_name = models.CharField(max_length=100)

    object_id = models.IntegerField(null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    details = models.TextField(blank=True)

    def __str__(self):
        return f"{self.action} - {self.timestamp}"


class DeviceLocationHistory(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="location_history")
    location_type = models.CharField(max_length=20, choices=Device.LOCATION_CHOICES)
    location = models.CharField(max_length=255)
    action = models.CharField(max_length=100)
    status = models.CharField(max_length=20, blank=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.device.company_tag} - {self.location} ({self.action})"
