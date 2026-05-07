"""
Serializers for all models.

Handles data validation and transformation for API requests/responses.
"""

from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from .models import (
    User,
    Branch,
    Department,
    Employee,
    Device,
    DeviceAssignment,
    RepairRequest,
    RepairLog,
    InventorySession,
    InventoryItem,
    Notification,
    AuditLog,
)

DEFAULT_EMPLOYEE_PASSWORD = "Aa@2026123"


# =========================
# USER SERIALIZERS
# =========================
class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "role",
            "is_active",
            "date_joined",
        )
        read_only_fields = ("id", "date_joined")


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating users."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("username", "email", "password", "role")

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


# =========================
# BRANCH SERIALIZERS
# =========================
class BranchSerializer(serializers.ModelSerializer):
    """Serializer for Branch model."""

    manager_name = serializers.CharField(
        source="manager.full_name", read_only=True
    )

    class Meta:
        model = Branch
        fields = ("id", "name", "location", "manager", "manager_name")
        read_only_fields = ("id",)


# =========================
# DEPARTMENT SERIALIZERS
# =========================
class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model."""

    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = Department
        fields = ("id", "name", "branch", "branch_name")
        read_only_fields = ("id",)


# =========================
# EMPLOYEE SERIALIZERS
# =========================
class EmployeeSerializer(serializers.ModelSerializer):
    """Serializer for Employee model."""

    user_username = serializers.CharField(
        source="user.username", read_only=True
    )
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    department_name = serializers.CharField(
        source="department.name", read_only=True
    )
    login_username = serializers.CharField(write_only=True, required=False, allow_blank=False)
    login_email = serializers.EmailField(write_only=True, required=False, allow_blank=False)
    login_role = serializers.ChoiceField(
        write_only=True,
        choices=(
            ("EMPLOYEE", "Employee"),
            ("BRANCH_MANAGER", "Branch Manager"),
            ("TECHNICIAN", "Technician"),
        ),
        required=False,
        default="EMPLOYEE",
    )
    generated_username = serializers.CharField(source="user.username", read_only=True)
    generated_email = serializers.EmailField(source="user.email", read_only=True)
    default_password = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = (
            "id",
            "user",
            "user_username",
            "full_name",
            "position",
            "branch",
            "branch_name",
            "department",
            "department_name",
            "status",
            "hire_date",
            "exit_date",
            "login_username",
            "login_email",
            "login_role",
            "generated_username",
            "generated_email",
            "default_password",
        )
        read_only_fields = ("id", "generated_username", "generated_email", "default_password")

    def get_default_password(self, obj):
        if self.context.get("include_default_password") and getattr(obj, "_generated_default_password", False):
            return DEFAULT_EMPLOYEE_PASSWORD
        return None

    def validate(self, attrs):
        if self.instance is None and not attrs.get("user"):
            errors = {}
            if not attrs.get("login_username"):
                errors["login_username"] = "Username is required."
            if not attrs.get("login_email"):
                errors["login_email"] = "Email is required."
            if errors:
                raise serializers.ValidationError(errors)

        login_role = attrs.get("login_role", "EMPLOYEE")
        branch = attrs.get("branch") or getattr(self.instance, "branch", None)
        if login_role != "TECHNICIAN" and self.instance is None and not branch:
            raise serializers.ValidationError({"branch": "Branch is required."})

        department = attrs.get("department")
        if department and branch and department.branch_id != branch.id:
            raise serializers.ValidationError(
                {"department": "Department must belong to the selected branch."}
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        login_username = validated_data.pop("login_username", "").strip()
        login_email = validated_data.pop("login_email", "").strip()
        login_role = validated_data.pop("login_role", "EMPLOYEE")
        user = validated_data.get("user")
        created_user = False

        if not user:
            username = login_username
            email = login_email

            if User.objects.filter(username=username).exists():
                raise serializers.ValidationError({"login_username": "Username already exists."})
            if User.objects.filter(email=email).exists():
                raise serializers.ValidationError({"login_email": "Email already exists."})

            user = User.objects.create_user(
                username=username,
                email=email,
                password=DEFAULT_EMPLOYEE_PASSWORD,
                role=login_role,
            )
            validated_data["user"] = user
            created_user = True

        employee = super().create(validated_data)
        if employee.user and employee.user.role == "BRANCH_MANAGER" and employee.branch:
            employee.branch.manager = employee
            employee.branch.save(update_fields=["manager"])
        if created_user:
            employee._generated_default_password = True
        return employee


class EmployeeListSerializer(serializers.ModelSerializer):
    """List serializer for Employee model."""

    branch_name = serializers.CharField(source="branch.name", read_only=True)
    status = serializers.CharField()
    assigned_devices = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = (
            "id",
            "full_name",
            "position",
            "branch_name",
            "status",
            "assigned_devices",
        )
        read_only_fields = ("id",)

    def get_assigned_devices(self, obj):
        return [
            {
                "device_name": f"{device.brand} {device.model}".strip(),
                "device_tag": device.company_tag,
                "device_serial_number": device.serial_number,
                "department": obj.department.name if obj.department else None,
            }
            for device in obj.device_set.all()
        ]


# =========================
# DEVICE SERIALIZERS
# =========================
class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for Device model."""

    assigned_employee_name = serializers.CharField(
        source="assigned_employee.full_name", read_only=True
    )
    assigned_branch_name = serializers.CharField(
        source="assigned_branch.name", read_only=True
    )
    days_assigned = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = (
            "id",
            "device_type",
            "brand",
            "model",
            "serial_number",
            "company_tag",
            "purchase_date",
            "warranty_expiry",
            "status",
            "assigned_employee",
            "assigned_employee_name",
            "assigned_branch",
            "assigned_branch_name",
            "location_type",
            "current_location",
            "condition_notes",
            "days_assigned",
        )
        read_only_fields = ("id", "days_assigned")

    def get_days_assigned(self, obj):
        """Calculate days since assignment."""
        if obj.assigned_employee:
            from datetime import datetime

            last_assignment = (
                DeviceAssignment.objects.filter(
                    device=obj, returned_date__isnull=True
                )
                .first()
            )
            if last_assignment:
                return (
                    timezone.now() - last_assignment.assigned_date
                ).days
        return None

    def validate(self, attrs):
        assigned_employee = attrs.get(
            "assigned_employee",
            getattr(self.instance, "assigned_employee", None),
        )
        assigned_branch = attrs.get(
            "assigned_branch",
            getattr(self.instance, "assigned_branch", None),
        )

        if assigned_employee and assigned_branch and assigned_employee.branch_id != assigned_branch.id:
            raise serializers.ValidationError(
                {
                    "assigned_employee": (
                        "Assigned employee must belong to the selected branch."
                    )
                }
            )

        return attrs


class DeviceListSerializer(serializers.ModelSerializer):
    """List serializer for Device model."""

    status = serializers.CharField()
    assigned_branch_name = serializers.CharField(source="assigned_branch.name", read_only=True)

    class Meta:
        model = Device
        fields = (
            "id",
            "device_type",
            "brand",
            "model",
            "serial_number",
            "company_tag",
            "status",
            "assigned_branch",
            "assigned_branch_name",
            "location_type",
        )
        read_only_fields = ("id",)


# =========================
# DEVICE ASSIGNMENT SERIALIZERS
# =========================
class DeviceAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for DeviceAssignment model."""

    device_info = DeviceSerializer(source="device", read_only=True)
    employee_name = serializers.CharField(
        source="employee.full_name", read_only=True
    )
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    assigned_by_username = serializers.CharField(
        source="assigned_by.username", read_only=True
    )
    received_by_username = serializers.CharField(
        source="received_by.username", read_only=True, allow_null=True
    )
    days_assigned = serializers.SerializerMethodField()

    class Meta:
        model = DeviceAssignment
        fields = (
            "id",
            "device",
            "device_info",
            "employee",
            "employee_name",
            "branch",
            "branch_name",
            "assigned_by",
            "assigned_by_username",
            "received_by",
            "received_by_username",
            "assigned_date",
            "returned_date",
            "condition_on_issue",
            "condition_on_return",
            "days_assigned",
        )
        read_only_fields = (
            "id",
            "assigned_date",
            "assigned_by",
            "days_assigned",
        )

    def get_days_assigned(self, obj):
        """Calculate days assigned."""
        if obj.returned_date:
            return (obj.returned_date - obj.assigned_date).days
        return (timezone.now() - obj.assigned_date).days


class DeviceAssignmentCreateSerializer(serializers.Serializer):
    """Serializer for creating device assignments."""

    device_id = serializers.IntegerField()
    employee_id = serializers.IntegerField()
    condition_on_issue = serializers.CharField(
        required=False, allow_blank=True
    )


# =========================
# REPAIR REQUEST SERIALIZERS
# =========================
class RepairRequestSerializer(serializers.ModelSerializer):
    """Serializer for RepairRequest model."""

    device_info = DeviceSerializer(source="device", read_only=True)
    employee_name = serializers.CharField(
        source="employee.full_name", read_only=True
    )
    approved_by_username = serializers.CharField(
        source="approved_by.username", read_only=True, allow_null=True
    )

    class Meta:
        model = RepairRequest
        fields = (
            "id",
            "device",
            "device_info",
            "employee",
            "employee_name",
            "issue_description",
            "priority",
            "status",
            "request_date",
            "approved_by",
            "approved_by_username",
        )
        read_only_fields = ("id", "request_date", "approved_by")


class RepairRequestListSerializer(serializers.ModelSerializer):
    """List serializer for RepairRequest model."""

    device_info = serializers.SerializerMethodField()
    employee_name = serializers.CharField(
        source="employee.full_name", read_only=True
    )

    class Meta:
        model = RepairRequest
        fields = (
            "id",
            "device_info",
            "employee_name",
            "issue_description",
            "priority",
            "status",
            "request_date",
        )
        read_only_fields = ("id",)

    def get_device_info(self, obj):
        return {
            "id": obj.device.id,
            "company_tag": obj.device.company_tag,
            "device_type": obj.device.device_type,
        }


# =========================
# REPAIR LOG SERIALIZERS
# =========================
class RepairLogSerializer(serializers.ModelSerializer):
    """Serializer for RepairLog model."""

    technician_username = serializers.CharField(
        source="technician.username", read_only=True, allow_null=True
    )
    repair_request_info = RepairRequestListSerializer(
        source="repair_request", read_only=True
    )

    class Meta:
        model = RepairLog
        fields = (
            "id",
            "repair_request",
            "repair_request_info",
            "technician",
            "technician_username",
            "notes",
            "parts_used",
            "start_date",
            "completed_date",
        )
        read_only_fields = ("id", "start_date")


# =========================
# INVENTORY SESSION SERIALIZERS
# =========================
class InventorySessionSerializer(serializers.ModelSerializer):
    """Serializer for InventorySession model."""

    branch_name = serializers.CharField(source="branch.name", read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, allow_null=True
    )

    class Meta:
        model = InventorySession
        fields = (
            "id",
            "branch",
            "branch_name",
            "start_date",
            "end_date",
            "created_by",
            "created_by_username",
            "approved_by_branch",
            "approved_by_head_office",
        )
        read_only_fields = ("id", "created_by", "created_by_username")


# =========================
# INVENTORY ITEM SERIALIZERS
# =========================
class InventoryItemSerializer(serializers.ModelSerializer):
    """Serializer for InventoryItem model."""

    device_info = DeviceSerializer(source="device", read_only=True)

    class Meta:
        model = InventoryItem
        fields = (
            "id",
            "session",
            "device",
            "device_info",
            "status",
            "comment",
        )
        read_only_fields = ("id",)


# =========================
# NOTIFICATION SERIALIZERS
# =========================
class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""

    class Meta:
        model = Notification
        fields = ("id", "user", "message", "is_read", "created_at")
        read_only_fields = ("id", "created_at")


# =========================
# AUDIT LOG SERIALIZERS
# =========================
class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model."""

    user_username = serializers.CharField(
        source="user.username", read_only=True, allow_null=True
    )

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "user",
            "user_username",
            "action",
            "model_name",
            "object_id",
            "timestamp",
            "details",
        )
        read_only_fields = (
            "id",
            "timestamp",
            "user",
            "action",
            "model_name",
            "object_id",
            "details",
        )
