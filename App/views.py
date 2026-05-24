"""
ViewSets for all API endpoints.

Implements REST API views with proper role-based access control,
pagination, filtering, and search capabilities.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Count, Min, Q
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import (
    User,
    Role,
    Module,
    Permission,
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
    DeviceLocationHistory,
)

from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    RoleSerializer,
    RoleOptionSerializer,
    ModuleSerializer,
    PermissionSerializer,
    BranchSerializer,
    DepartmentSerializer,
    EmployeeSerializer,
    EmployeeListSerializer,
    DeviceSerializer,
    DeviceListSerializer,
    DeviceAssignmentSerializer,
    DeviceAssignmentCreateSerializer,
    RepairRequestSerializer,
    RepairRequestListSerializer,
    RepairLogSerializer,
    InventorySessionSerializer,
    InventoryItemSerializer,
    NotificationSerializer,
    AuditLogSerializer,
    DeviceLocationHistorySerializer,
    DEFAULT_EMPLOYEE_PASSWORD,
)

from .permissions import (
    IsHeadOffice,
    IsTechnician,
    IsBranchManager,
    IsEmployee,
    IsOwnerOrReadOnly,
    CanManageDevices,
    CanManageAssignments,
    CanRequestRepair,
    CanApproveRepair,
    CanUpdateRepair,
    CanVerifyInventory,
    CanCreateInventorySession,
    HasAppPermission,
    HasAnyAppPermission,
)
from .decorators import role_required, permission_required
from .access_control import (
    SYSTEM_ROLE_LABELS,
    build_accessible_menu,
    get_user_permission_codenames,
    user_has_permission,
)

from .services import (
    DeviceAssignmentService,
    RepairService,
    InventoryService,
    EmployeeExitService,
    AuditService,
    DeviceLifecycleService,
)


DEACTIVATED_ACCOUNT_MESSAGE = "Your account has been deactivated. Please contact the administrator."

DEFAULT_DEPARTMENT_NAMES = [
    "Human Resources",
    "Finance",
    "Operations",
    "Information Technology",
    "Logistics",
    "Procurement",
    "Customer Service",
    "Maintenance",
]


def _notify_user(user, message):
    if user:
        Notification.objects.create(user=user, message=message)


def _notify_head_office(message):
    for user in User.objects.filter(role="HEAD_OFFICE", is_active=True):
        Notification.objects.create(user=user, message=message)


def _sync_employee_user_active_state(employee):
    if not employee.user:
        return
    should_be_active = employee.status == "ACTIVE"
    if employee.user.is_active != should_be_active:
        employee.user.is_active = should_be_active
        employee.user.save(update_fields=["is_active"])


def _include_deleted(request):
    return request.query_params.get("deleted") == "1" or request.GET.get("deleted") == "1"


def _deleted_only(request):
    return request.query_params.get("deleted") == "only" or request.GET.get("deleted") == "only"


def _activity_response(record_type, activities):
    return Response(
        {
            "error": "This record cannot be deleted because it has related activities.",
            "related_activities": activities,
            "record_type": record_type,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _soft_delete_instance(instance, user, model_name, details, reason=""):
    instance.soft_delete(user=user, reason=reason)
    AuditService.log_action(user, f"{model_name.upper()}_DELETED", model_name, instance.id, details)


def _restore_instance(instance, user, model_name, details):
    instance.restore(user=user)
    AuditService.log_action(user, f"{model_name.upper()}_RESTORED", model_name, instance.id, details)


def _branch_delete_activities(branch):
    activities = []
    if branch.employees.filter(is_deleted=False).exists():
        activities.append({"type": "Employees", "count": branch.employees.filter(is_deleted=False).count()})
    if Device.objects.filter(assigned_branch=branch, is_deleted=False).exists():
        activities.append({"type": "Assigned devices", "count": Device.objects.filter(assigned_branch=branch, is_deleted=False).count()})
    if InventorySession.objects.filter(branch=branch, is_deleted=False).exists():
        activities.append({"type": "Inventory sessions", "count": InventorySession.objects.filter(branch=branch, is_deleted=False).count()})
    return activities


def _department_delete_activities(department):
    activities = []
    if Employee.objects.filter(department=department, is_deleted=False).exists():
        activities.append({"type": "Employees", "count": Employee.objects.filter(department=department, is_deleted=False).count()})
    return activities


def _employee_delete_activities(employee):
    activities = []
    if Device.objects.filter(assigned_employee=employee, is_deleted=False).exists():
        activities.append({"type": "Assigned devices", "count": Device.objects.filter(assigned_employee=employee, is_deleted=False).count()})
    if DeviceAssignment.objects.filter(employee=employee).exists():
        activities.append({"type": "Assignment history", "count": DeviceAssignment.objects.filter(employee=employee).count()})
    if RepairRequest.objects.filter(employee=employee).exists():
        activities.append({"type": "Repair history", "count": RepairRequest.objects.filter(employee=employee).count()})
    if Branch.objects.filter(manager=employee, is_deleted=False).exists():
        activities.append({"type": "Managed branches", "count": Branch.objects.filter(manager=employee, is_deleted=False).count()})
    return activities


def _device_delete_activities(device):
    activities = []
    if device.assignments.exists():
        activities.append({"type": "Assignment history", "count": device.assignments.count()})
    if RepairRequest.objects.filter(device=device).exists():
        activities.append({"type": "Repair history", "count": RepairRequest.objects.filter(device=device).count()})
    if InventoryItem.objects.filter(device=device).exists():
        activities.append({"type": "Inventory records", "count": InventoryItem.objects.filter(device=device).count()})
    return activities


def _inventory_delete_activities(session):
    activities = []
    if session.items.exists():
        activities.append({"type": "Inventory transactions", "count": session.items.count()})
    return activities


# =========================
# USER VIEWSET
# =========================
class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing users.

    - list: Get all users (HEAD_OFFICE only)
    - create: Create new user (HEAD_OFFICE only)
    - retrieve: Get user details
    - update: Update user (own user or HEAD_OFFICE)
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["username", "email"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ["list", "create"]:
            return [HasAppPermission("view_access_control" if self.action == "list" else "add_employee")]
        if self.action == "retrieve":
            return [HasAppPermission("view_access_control")]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Set user as inactive by default."""
        serializer.save(is_active=True)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        data = serializer.data
        data["permissions"] = get_user_permission_codenames(request.user)
        data["menu"] = build_accessible_menu(request.user)
        return Response(data)


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.prefetch_related("permissions", "permissions__module")
    serializer_class = RoleSerializer
    permission_classes = [IsHeadOffice]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering = ["name"]

    def get_permissions(self):
        action_permissions = {
            "list": "view_access_control",
            "retrieve": "view_access_control",
            "options": "view_access_control",
            "create": "add_role",
            "update": "update_role",
            "partial_update": "update_role",
            "destroy": "delete_role",
            "assign_user": "assign_role",
            "unassign_user": "assign_role",
        }
        return [HasAppPermission(action_permissions.get(self.action, "view_access_control"))]

    def destroy(self, request, *args, **kwargs):
        role = self.get_object()
        if role.is_system:
            return Response({"error": "System roles cannot be deleted."}, status=status.HTTP_400_BAD_REQUEST)
        if role.users.exists():
            return Response({"error": "Remove this role from users before deleting it."}, status=status.HTTP_400_BAD_REQUEST)
        role_id = role.id
        role_name = role.name
        response = super().destroy(request, *args, **kwargs)
        AuditService.log_action(request.user, "ROLE_DELETED", "Role", role_id, f"Role deleted: {role_name}")
        return response

    def perform_create(self, serializer):
        role = serializer.save()
        permission_names = ", ".join(role.permissions.values_list("permission_name", flat=True))
        AuditService.log_action(
            self.request.user,
            "ROLE_CREATED",
            "Role",
            role.id,
            f"Role created: {role.name}; permissions: {permission_names or 'none'}",
        )

    def perform_update(self, serializer):
        role = self.get_object()
        before = set(role.permissions.values_list("codename", flat=True))
        role = serializer.save()
        after = set(role.permissions.values_list("codename", flat=True))
        added = sorted(after - before)
        removed = sorted(before - after)
        AuditService.log_action(
            self.request.user,
            "ROLE_UPDATED",
            "Role",
            role.id,
            f"Role updated: {role.name}; added permissions: {', '.join(added) or 'none'}; removed permissions: {', '.join(removed) or 'none'}",
        )

    @action(detail=False, methods=["get"])
    def options(self, request):
        roles = Role.objects.all().order_by("is_system", "name")
        return Response(RoleOptionSerializer(roles, many=True).data)

    @action(detail=True, methods=["post"])
    def assign_user(self, request, pk=None):
        role = self.get_object()
        user = get_object_or_404(User, pk=request.data.get("user_id"))
        user.dynamic_role = None if role.is_system else role
        if role.code in SYSTEM_ROLE_LABELS:
            user.role = role.code
        elif user.role == "HEAD_OFFICE":
            return Response({"error": "Head Office users cannot be downgraded through role assignment."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            user.role = "EMPLOYEE"
        user.save(update_fields=["role", "dynamic_role"])
        AuditService.log_action(request.user, "ROLE_ASSIGNED", "User", user.id, f"{user.username} -> {role.name}")
        return Response(UserSerializer(user).data)

    @action(detail=False, methods=["post"])
    def unassign_user(self, request):
        user = get_object_or_404(User, pk=request.data.get("user_id"))
        if user.role == "HEAD_OFFICE":
            return Response({"error": "Head Office role cannot be removed."}, status=status.HTTP_400_BAD_REQUEST)
        user.dynamic_role = None
        user.role = "EMPLOYEE"
        user.save(update_fields=["role", "dynamic_role"])
        AuditService.log_action(request.user, "ROLE_REMOVED", "User", user.id, f"{user.username} -> Employee")
        return Response(UserSerializer(user).data)


class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.prefetch_related("permissions")
    serializer_class = ModuleSerializer
    permission_classes = [IsHeadOffice]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["module_name", "description"]
    ordering = ["module_name"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [HasAppPermission("manage_permissions")]
        return [HasAppPermission("view_access_control")]

    def perform_create(self, serializer):
        module = serializer.save()
        AuditService.log_action(self.request.user, "MODULE_CREATED", "Module", module.id, f"Module created: {module.module_name}")

    def perform_update(self, serializer):
        module = serializer.save()
        AuditService.log_action(self.request.user, "MODULE_UPDATED", "Module", module.id, f"Module updated: {module.module_name}")

    def perform_destroy(self, instance):
        module_id = instance.id
        module_name = instance.module_name
        instance.delete()
        AuditService.log_action(self.request.user, "MODULE_DELETED", "Module", module_id, f"Module deleted: {module_name}")


class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.select_related("module")
    serializer_class = PermissionSerializer
    permission_classes = [IsHeadOffice]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["module"]
    search_fields = ["permission_name", "codename", "module__module_name"]
    ordering = ["module__module_name", "permission_name"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [HasAppPermission("manage_permissions")]
        return [HasAppPermission("view_access_control")]

    def perform_create(self, serializer):
        permission = serializer.save()
        AuditService.log_action(
            self.request.user,
            "PERMISSION_CREATED",
            "Permission",
            permission.id,
            f"Permission created: {permission.permission_name} ({permission.codename})",
        )

    def perform_update(self, serializer):
        permission = serializer.save()
        AuditService.log_action(
            self.request.user,
            "PERMISSION_UPDATED",
            "Permission",
            permission.id,
            f"Permission updated: {permission.permission_name} ({permission.codename})",
        )

    def perform_destroy(self, instance):
        permission_id = instance.id
        permission_name = instance.permission_name
        instance.delete()
        AuditService.log_action(
            self.request.user,
            "PERMISSION_DELETED",
            "Permission",
            permission_id,
            f"Permission deleted: {permission_name}",
        )


class AccessControlViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(
            {
                "role": request.user.role,
                "role_name": request.user.effective_role_name,
                "permissions": get_user_permission_codenames(request.user),
                "menu": build_accessible_menu(request.user),
            }
        )


# =========================
# BRANCH VIEWSET
# =========================
class BranchViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing branches.

    - list: Get all branches
    - create: Create branch (HEAD_OFFICE only)
    - retrieve: Get branch details
    - update: Update branch (HEAD_OFFICE only)
    """

    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "location"]
    ordering_fields = ["name"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = Branch.objects.all()
        if _deleted_only(self.request):
            return queryset.filter(is_deleted=True)
        if not _include_deleted(self.request):
            queryset = queryset.filter(is_deleted=False)
        return queryset

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            action_permissions = {
                "create": "add_branch",
                "update": "update_branch",
                "partial_update": "update_branch",
                "destroy": "delete_branch",
            }
            return [HasAppPermission(action_permissions[self.action])]
        if self.action in ["list", "retrieve"]:
            return [HasAppPermission("view_branch")]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        branch = serializer.save()
        existing_department_names = list(Department.objects.values_list("name", flat=True).distinct())
        department_names = existing_department_names or DEFAULT_DEPARTMENT_NAMES
        for name in department_names:
            Department.objects.get_or_create(branch=branch, name=name)
        AuditService.log_action(
            self.request.user,
            "BRANCH_CREATED",
            "Branch",
            branch.id,
            f"Branch: {branch.name}",
        )

    def perform_update(self, serializer):
        branch = serializer.save()
        AuditService.log_action(
            self.request.user,
            "BRANCH_UPDATED",
            "Branch",
            branch.id,
            f"Branch: {branch.name}",
        )

    def perform_destroy(self, instance):
        activities = _branch_delete_activities(instance)
        if activities:
            raise DjangoValidationError("This record cannot be deleted because it has related activities.")
        branch_id = instance.id
        branch_name = instance.name
        _soft_delete_instance(
            instance,
            self.request.user,
            "Branch",
            f"Branch: {branch_name}",
            self.request.data.get("reason", "") if hasattr(self.request, "data") else "",
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        activities = _branch_delete_activities(instance)
        if activities:
            return _activity_response("Branch", activities)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOffice])
    def restore(self, request, pk=None):
        branch = get_object_or_404(Branch.objects.all(), pk=pk)
        _restore_instance(branch, request.user, "Branch", f"Branch: {branch.name}")
        return Response(self.get_serializer(branch).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["delete"], permission_classes=[IsHeadOffice])
    def permanent_delete(self, request, pk=None):
        branch = get_object_or_404(Branch.objects.all(), pk=pk)
        activities = _branch_delete_activities(branch)
        if activities:
            return _activity_response("Branch", activities)
        branch_id = branch.id
        branch_name = branch.name
        branch.delete()
        AuditService.log_action(
            request.user,
            "BRANCH_PERMANENTLY_DELETED",
            "Branch",
            branch_id,
            f"Branch: {branch_name}",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# =========================
# DEPARTMENT VIEWSET
# =========================
class DepartmentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing departments.

    - list: Get all departments
    - create: Create department (HEAD_OFFICE only)
    """

    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["branch"]
    search_fields = ["name"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = Department.objects.select_related("branch")
        if _deleted_only(self.request):
            return queryset.filter(is_deleted=True)
        if not _include_deleted(self.request):
            queryset = queryset.filter(is_deleted=False, branch__is_deleted=False)
        return queryset

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            action_permissions = {
                "create": "add_department",
                "update": "update_department",
                "partial_update": "update_department",
                "destroy": "delete_department",
            }
            return [HasAppPermission(action_permissions[self.action])]
        if self.action in ["list", "retrieve"]:
            return [HasAppPermission("view_department")]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        requested_branch = serializer.validated_data.get("branch")
        name = serializer.validated_data["name"].strip()
        if requested_branch:
            department, _ = Department.objects.get_or_create(
                branch=requested_branch,
                name=name,
            )
        else:
            department = None
        for branch in Branch.objects.filter(is_deleted=False):
            department, _ = Department.objects.get_or_create(branch=branch, name=name)
        AuditService.log_action(
            self.request.user,
            "DEPARTMENT_CREATED",
            "Department",
            department.id,
            f"Department: {department.name}",
        )

    def create(self, request, *args, **kwargs):
        name = request.data.get("name", "").strip()
        if not name:
            return Response({"name": "Department name is required."}, status=status.HTTP_400_BAD_REQUEST)
        first_branch = Branch.objects.first()
        if not first_branch:
            return Response({"error": "Create a branch before registering departments."}, status=status.HTTP_400_BAD_REQUEST)
        data = request.data.copy()
        data["name"] = name
        data["branch"] = data.get("branch") or first_branch.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        department = Department.objects.filter(name=name).order_by("id").first()
        return Response(self.get_serializer(department).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        department = self.get_object()
        old_name = department.name
        new_name = request.data.get("name", "").strip()
        if not new_name:
            return Response({"name": "Department name is required."}, status=status.HTTP_400_BAD_REQUEST)

        Department.objects.filter(name=old_name).update(name=new_name)
        updated = Department.objects.filter(name=new_name).order_by("id").first()
        AuditService.log_action(
            request.user,
            "DEPARTMENT_UPDATED",
            "Department",
            updated.id if updated else department.id,
            f"Department: {old_name} -> {new_name}",
        )
        return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        department = self.get_object()
        old_name = department.name
        departments = Department.objects.filter(name=old_name)
        activities = []
        for item in departments:
            activities.extend(_department_delete_activities(item))
        if activities:
            return _activity_response("Department", activities)
        departments.update(
            is_deleted=True,
            deleted_at=timezone.now(),
            deleted_by_id=request.user.id,
            deletion_reason=request.data.get("reason", ""),
        )
        AuditService.log_action(
            request.user,
            "DEPARTMENT_DELETED",
            "Department",
            department.id,
            f"Department: {old_name}",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOffice])
    def restore(self, request, pk=None):
        department = get_object_or_404(Department.objects.all(), pk=pk)
        Department.objects.filter(name=department.name).update(
            is_deleted=False,
            deleted_at=None,
            deleted_by_id=None,
            deletion_reason="",
        )
        AuditService.log_action(request.user, "DEPARTMENT_RESTORED", "Department", department.id, f"Department: {department.name}")
        return Response(self.get_serializer(department).data, status=status.HTTP_200_OK)


# =========================
# EMPLOYEE VIEWSET
# =========================
class EmployeeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing employees.

    - list: Get all employees
    - create: Create employee (HEAD_OFFICE only)
    - retrieve: Get employee details
    - set_exit_status: Mark employee as exited (HEAD_OFFICE only)
    - reset_password: Reset employee login to default password (HEAD_OFFICE only)
    """

    queryset = Employee.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["branch", "status"]
    search_fields = ["full_name", "position"]
    ordering = ["full_name"]

    def get_queryset(self):
        queryset = Employee.objects.select_related("user", "branch", "department")
        if _deleted_only(self.request):
            return queryset.filter(is_deleted=True)
        if not _include_deleted(self.request):
            queryset = queryset.filter(is_deleted=False)
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return EmployeeListSerializer
        return EmployeeSerializer

    def get_permissions(self):
        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
            "set_exit_status",
            "reset_password",
            "activity",
        ]:
            action_permissions = {
                "create": "add_employee",
                "update": "update_employee",
                "partial_update": "update_employee",
                "destroy": "delete_employee",
                "set_exit_status": "update_employee",
                "reset_password": "reset_employee_password",
                "activity": "assign_role",
            }
            return [HasAppPermission(action_permissions[self.action])]
        if self.action in ["list", "retrieve"]:
            return [HasAnyAppPermission("view_employee", "view_branch_employees")]
        return [IsAuthenticated()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == "create":
            context["include_default_password"] = True
        return context

    def perform_create(self, serializer):
        employee = serializer.save()
        _sync_employee_user_active_state(employee)
        AuditService.log_action(
            self.request.user,
            "EMPLOYEE_CREATED",
            "Employee",
            employee.id,
            f"Employee: {employee.full_name}; username: {employee.user.username if employee.user else 'none'}",
        )

    def perform_update(self, serializer):
        employee = serializer.save()
        _sync_employee_user_active_state(employee)
        AuditService.log_action(
            self.request.user,
            "EMPLOYEE_UPDATED",
            "Employee",
            employee.id,
            f"Employee: {employee.full_name}",
        )

    def perform_destroy(self, instance):
        employee_name = instance.full_name
        _soft_delete_instance(
            instance,
            self.request.user,
            "Employee",
            f"Employee: {employee_name}",
            self.request.data.get("reason", "") if hasattr(self.request, "data") else "",
        )
        if instance.user:
            instance.user.is_active = False
            instance.user.save(update_fields=["is_active"])

    def destroy(self, request, *args, **kwargs):
        employee = self.get_object()
        activities = _employee_delete_activities(employee)
        if activities:
            return _activity_response("Employee", activities)
        self.perform_destroy(employee)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOffice])
    def restore(self, request, pk=None):
        employee = get_object_or_404(Employee.objects.all(), pk=pk)
        _restore_instance(employee, request.user, "Employee", f"Employee: {employee.full_name}")
        _sync_employee_user_active_state(employee)
        return Response(self.get_serializer(employee).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["delete"], permission_classes=[IsHeadOffice])
    def permanent_delete(self, request, pk=None):
        employee = get_object_or_404(Employee.objects.all(), pk=pk)
        activities = _employee_delete_activities(employee)
        if activities:
            return _activity_response("Employee", activities)
        employee_id = employee.id
        employee_name = employee.full_name
        user = employee.user
        employee.delete()
        if user:
            user.delete()
        AuditService.log_action(
            request.user,
            "EMPLOYEE_PERMANENTLY_DELETED",
            "Employee",
            employee_id,
            f"Employee: {employee_name}",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOffice])
    def set_exit_status(self, request, pk=None):
        """
        Mark employee as exited and handle device returns.

        POST /api/employees/{id}/set_exit_status/
        """
        employee = self.get_object()
        exit_date = request.data.get("exit_date")

        if not exit_date:
            return Response(
                {"error": "exit_date is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        employee.status = "EXITED"
        employee.exit_date = exit_date
        employee.save()
        _sync_employee_user_active_state(employee)

        # Handle employee exit
        affected_devices = EmployeeExitService.handle_employee_exit(
            employee.id
        )

        AuditService.log_action(
            request.user,
            "EMPLOYEE_EXITED",
            "Employee",
            employee.id,
            f"Exit date: {exit_date}",
        )

        return Response(
            {
                "message": f"Employee marked as exited. {len(affected_devices)} devices marked for return.",
                "affected_devices": len(affected_devices),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOffice])
    def reset_password(self, request, pk=None):
        """
        Reset an employee login password to the system default.

        POST /api/employees/{id}/reset_password/
        """
        employee = self.get_object()
        if not employee.user:
            return Response(
                {"error": "This employee does not have a login account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        employee.user.set_password(DEFAULT_EMPLOYEE_PASSWORD)
        employee.user.must_change_password = True
        employee.user.save(update_fields=["password", "must_change_password"])

        AuditService.log_action(
            request.user,
            "EMPLOYEE_PASSWORD_RESET",
            "Employee",
            employee.id,
            f"Password reset for employee: {employee.full_name}; username: {employee.user.username}",
        )

        return Response(
            {
                "message": "Employee password reset successfully. The employee must change it before accessing the system.",
                "default_password": DEFAULT_EMPLOYEE_PASSWORD,
                "must_change_password": True,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def activity(self, request, pk=None):
        employee = self.get_object()
        user = employee.user
        logs = AuditLog.objects.select_related("user").filter(user=user).order_by("-timestamp")[:50] if user else []
        return Response(
            {
                "employee": {
                    "id": employee.id,
                    "employee_id": employee.employee_id,
                    "full_name": employee.full_name,
                    "position": employee.position,
                    "branch": employee.branch.name if employee.branch else None,
                    "department": employee.department.name if employee.department else None,
                    "status": employee.status,
                    "role": user.effective_role_name if user else None,
                    "username": user.username if user else None,
                    "email": user.email if user else None,
                    "date_joined": user.date_joined if user else None,
                },
                "activity": [
                    {
                        "action": log.action,
                        "model_name": log.model_name,
                        "object_id": log.object_id,
                        "timestamp": log.timestamp,
                        "details": log.details,
                    }
                    for log in logs
                ],
            }
        )


# =========================
# DEVICE VIEWSET
# =========================
class DeviceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing devices.

    - list: Get all devices (with filtering and search)
    - create: Create device (HEAD_OFFICE only)
    - retrieve: Get device details
    - update: Update device (HEAD_OFFICE only)
    """

    queryset = Device.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "device_type", "assigned_branch"]
    search_fields = ["serial_number", "company_tag", "model"]
    ordering_fields = ["status", "purchase_date"]
    ordering = ["-purchase_date"]

    def get_queryset(self):
        queryset = Device.objects.select_related("assigned_employee", "assigned_branch")
        if _deleted_only(self.request):
            queryset = queryset.filter(is_deleted=True)
        elif not _include_deleted(self.request):
            queryset = queryset.filter(is_deleted=False)
        user = self.request.user
        if user.is_authenticated and user.role == "EMPLOYEE" and not getattr(user, "dynamic_role_id", None):
            return queryset.filter(assigned_employee__user=user)
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return DeviceListSerializer
        return DeviceSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "decommission", "restore", "permanent_delete"]:
            return [CanManageDevices()]
        if self.action in ["list", "retrieve", "location_history"]:
            return [HasAnyAppPermission("view_device", "view_branch_devices", "view_my_devices", "diagnose_device_issue", "view_device_audit")]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Set created device as available."""
        device = serializer.save(status="AVAILABLE")
        DeviceLocationHistory.objects.create(
            device=device,
            location_type=device.location_type,
            location=device.current_location,
            action="DEVICE_CREATED",
            status=device.status,
            updated_by=self.request.user,
            notes="Initial device location",
        )
        AuditService.log_action(
            self.request.user,
            "DEVICE_CREATED",
            "Device",
            device.id,
            f"Device: {device.company_tag}",
        )

    def perform_update(self, serializer):
        device = serializer.save()
        AuditService.log_action(
            self.request.user,
            "DEVICE_UPDATED",
            "Device",
            device.id,
            f"Device: {device.company_tag}",
        )

    def perform_destroy(self, instance):
        device_id = instance.id
        device_tag = instance.company_tag
        _soft_delete_instance(
            instance,
            self.request.user,
            "Device",
            f"Device: {device_tag}",
            self.request.data.get("reason", "") if hasattr(self.request, "data") else "",
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        activities = _device_delete_activities(instance)
        if activities:
            return _activity_response("Device", activities)

        try:
            return super().destroy(request, *args, **kwargs)
        except DjangoValidationError as exc:
            return Response({"error": "; ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], permission_classes=[CanManageDevices])
    def restore(self, request, pk=None):
        device = get_object_or_404(Device.objects.all(), pk=pk)
        _restore_instance(device, request.user, "Device", f"Device: {device.company_tag}")
        return Response(self.get_serializer(device).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[CanManageDevices])
    def decommission(self, request, pk=None):
        reason = request.data.get("reason", "").strip()
        notes = request.data.get("notes", "").strip()
        try:
            device = DeviceLifecycleService.decommission_device(pk, request.user, reason, notes)
            return Response(self.get_serializer(device).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def location_history(self, request, pk=None):
        device = get_object_or_404(Device.objects.all(), pk=pk)
        history = device.location_history.select_related("updated_by").all()
        return Response(DeviceLocationHistorySerializer(history, many=True).data)

    @action(detail=True, methods=["delete"], permission_classes=[CanManageDevices])
    def permanent_delete(self, request, pk=None):
        device = get_object_or_404(Device.objects.all(), pk=pk)
        activities = _device_delete_activities(device)
        if activities:
            return _activity_response("Device", activities)
        device_id = device.id
        device_tag = device.company_tag
        device.delete()
        AuditService.log_action(
            request.user,
            "DEVICE_PERMANENTLY_DELETED",
            "Device",
            device_id,
            f"Device: {device_tag}",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# =========================
# DEVICE ASSIGNMENT VIEWSET
# =========================
class DeviceAssignmentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for device assignments.

    - list: Get all assignments
    - create: Create assignment (HEAD_OFFICE only)
    - retrieve: Get assignment details
    - return_device: Return assigned device (HEAD_OFFICE only)
    """

    queryset = DeviceAssignment.objects.all()
    serializer_class = DeviceAssignmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["employee", "branch", "returned_date"]
    search_fields = ["device__company_tag", "employee__full_name"]
    ordering = ["-assigned_date"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "return_device"]:
            return [CanManageAssignments()]
        if self.action in ["list", "retrieve"]:
            return [HasAppPermission("view_assignment")]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        """Create device assignment."""
        serializer = DeviceAssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            assignment = DeviceAssignmentService.assign_device(
                device_id=serializer.validated_data["device_id"],
                employee_id=serializer.validated_data["employee_id"],
                assigned_by_user=request.user,
                condition=serializer.validated_data.get(
                    "condition_on_issue"
                ),
            )

            output_serializer = DeviceAssignmentSerializer(assignment)
            return Response(
                output_serializer.data, status=status.HTTP_201_CREATED
            )

        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"], permission_classes=[CanManageAssignments])
    def return_device(self, request, pk=None):
        """
        Return assigned device.

        POST /api/assignments/{id}/return_device/
        """
        assignment = self.get_object()
        condition_on_return = request.data.get("condition_on_return")

        try:
            returned_assignment = (
                DeviceAssignmentService.return_device(
                    assignment.id,
                    request.user,
                    condition_on_return,
                )
            )

            serializer = DeviceAssignmentSerializer(returned_assignment)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    def perform_update(self, serializer):
        assignment = serializer.save()
        AuditService.log_action(
            self.request.user,
            "ASSIGNMENT_UPDATED",
            "DeviceAssignment",
            assignment.id,
            f"Assignment for {assignment.device.company_tag}",
        )

    def perform_destroy(self, instance):
        assignment_id = instance.id
        device = instance.device
        was_active = instance.returned_date is None
        instance.delete()
        if was_active:
            device.status = "AVAILABLE"
            device.assigned_employee = None
            device.assigned_branch = None
            device.location_type = "HEAD_OFFICE"
            device.current_location = "Head Office"
            device.save()
        AuditService.log_action(
            self.request.user,
            "ASSIGNMENT_DELETED",
            "DeviceAssignment",
            assignment_id,
            f"Assignment for {device.company_tag}",
        )


# =========================
# REPAIR REQUEST VIEWSET
# =========================
class RepairRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint for repair requests.

    - list: Get all repair requests
    - create: Create repair request (EMPLOYEE only)
    - approve: Approve repair (HEAD_OFFICE only)
    - reject: Reject repair (HEAD_OFFICE only)
    """

    queryset = RepairRequest.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "priority", "employee"]
    search_fields = ["device__company_tag", "issue_description"]
    ordering = ["-request_date"]

    def get_queryset(self):
        queryset = RepairRequest.objects.select_related(
            "device",
            "device__assigned_branch",
            "device__assigned_employee",
            "employee",
            "approved_by",
        )
        user = self.request.user
        if user.is_authenticated and user.role == "EMPLOYEE" and not getattr(user, "dynamic_role_id", None):
            return queryset.filter(employee__user=user)
        if user.is_authenticated and user.role == "TECHNICIAN" and not getattr(user, "dynamic_role_id", None):
            return queryset.filter(
                Q(repairlog__technician=user)
                | Q(status="APPROVED", repairlog__isnull=True)
            )
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return RepairRequestListSerializer
        return RepairRequestSerializer

    def get_permissions(self):
        if self.action == "create":
            return [HasAppPermission("request_repair")]
        elif self.action in ["approve", "reject", "reassign_completed"]:
            return [CanApproveRepair()]
        elif self.action in ["update", "partial_update", "destroy"]:
            return [HasAppPermission("update_repair")]
        elif self.action in ["list", "retrieve"]:
            return [HasAnyAppPermission("view_repairs", "view_technician_repairs", "view_my_repair_requests")]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        """Create repair request by employee."""
        device_id = request.data.get("device_id")
        issue_description = request.data.get("issue_description")
        priority = request.data.get("priority", "NORMAL")

        if not device_id or not issue_description:
            return Response(
                {
                    "error": "device_id and issue_description are required"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        employee_id = request.data.get("employee_id")
        if request.user.role == "HEAD_OFFICE" and employee_id:
            try:
                employee = Employee.objects.get(id=employee_id)
            except Employee.DoesNotExist:
                return Response({"error": "Employee profile not found"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                employee = Employee.objects.get(user=request.user)
            except Employee.DoesNotExist:
                return Response(
                    {"error": "Employee profile not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            repair_request = RepairService.create_repair_request(
                device_id=device_id,
                employee_id=employee.id,
                issue_description=issue_description,
                priority=priority,
            )

            serializer = RepairRequestSerializer(repair_request)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED
            )

        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    def perform_update(self, serializer):
        repair_request = serializer.save()
        AuditService.log_action(
            self.request.user,
            "REPAIR_REQUEST_UPDATED",
            "RepairRequest",
            repair_request.id,
            f"Repair request for {repair_request.device.company_tag}",
        )

    def perform_destroy(self, instance):
        repair_id = instance.id
        device_tag = instance.device.company_tag
        instance.delete()
        AuditService.log_action(
            self.request.user,
            "REPAIR_REQUEST_DELETED",
            "RepairRequest",
            repair_id,
            f"Repair request for {device_tag}",
        )

    @action(
        detail=True, methods=["post"], permission_classes=[IsHeadOffice]
    )
    def approve(self, request, pk=None):
        """
        Approve repair request.

        POST /api/repair-requests/{id}/approve/
        """
        repair_request = self.get_object()
        technician_id = request.data.get("technician_id") or request.data.get("technician")
        if technician_id:
            try:
                technician = User.objects.get(id=technician_id, role="TECHNICIAN", is_active=True)
            except (User.DoesNotExist, TypeError, ValueError):
                return Response(
                    {"error": "Select an active technician before approving this repair request."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            technician = User.objects.filter(role="TECHNICIAN", is_active=True).order_by("id").first()

        try:
            approved_request = RepairService.approve_repair(
                repair_request.id, request.user, technician
            )

            serializer = RepairRequestSerializer(approved_request)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True, methods=["post"], permission_classes=[IsHeadOffice]
    )
    def reject(self, request, pk=None):
        """
        Reject repair request.

        POST /api/repair-requests/{id}/reject/
        """
        repair_request = self.get_object()

        try:
            rejected_request = RepairService.reject_repair(
                repair_request.id, request.user
            )

            serializer = RepairRequestSerializer(rejected_request)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"], permission_classes=[CanUpdateRepair])
    def start_repair(self, request, pk=None):
        """Receive an approved repair request into technician work."""
        repair_request = self.get_object()
        notes = request.data.get("notes", "")
        parts_used = request.data.get("parts_used", "")
        work_start_date = parse_datetime(request.data.get("work_start_date", "")) if request.data.get("work_start_date") else None
        completion_date = parse_datetime(request.data.get("completion_date", "")) if request.data.get("completion_date") else None

        try:
            repair_log = RepairService.start_repair(
                repair_request.id,
                request.user,
                notes,
                parts_used,
                work_start_date,
                completion_date,
            )
            return Response(RepairLogSerializer(repair_log).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], permission_classes=[CanUpdateRepair])
    def complete_repair(self, request, pk=None):
        """Complete an approved or in-progress repair request."""
        repair_request = self.get_object()
        notes = request.data.get("notes")
        parts_used = request.data.get("parts_used", "")

        if not notes:
            return Response({"error": "notes is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            repair_log = RepairService.complete_repair(
                repair_request.id,
                request.user,
                notes,
                parts_used,
            )
            return Response(RepairLogSerializer(repair_log).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOffice])
    def reassign_completed(self, request, pk=None):
        """Reassign a completed repaired device back to its requesting employee."""
        repair_request = self.get_object()
        if repair_request.status != "COMPLETED":
            return Response(
                {"error": "Only completed repairs can be reassigned."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        condition = request.data.get("condition_on_issue", "Reassigned after completed repair")
        try:
            assignment = RepairService.reassign_completed_repair(
                repair_request_id=repair_request.id,
                reassigned_by_user=request.user,
                condition=condition,
            )
            return Response(
                DeviceAssignmentSerializer(assignment).data,
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =========================
# REPAIR LOG VIEWSET
# =========================
class RepairLogViewSet(viewsets.ModelViewSet):
    """
    API endpoint for repair logs.

    - list: Get all repair logs
    - update_repair: Complete repair (TECHNICIAN only)
    """

    queryset = RepairLog.objects.all()
    serializer_class = RepairLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = [
        "repair_request__device__company_tag",
        "technician__username",
    ]
    ordering = ["-start_date"]

    def get_queryset(self):
        queryset = RepairLog.objects.select_related(
            "repair_request",
            "repair_request__device",
            "repair_request__employee",
            "technician",
        )
        user = self.request.user
        if user.is_authenticated and user.role == "TECHNICIAN" and not getattr(user, "dynamic_role_id", None):
            return queryset.filter(Q(technician=user) | Q(repair_request__status="COMPLETED"))
        if user.is_authenticated and user.role == "EMPLOYEE" and not getattr(user, "dynamic_role_id", None):
            return queryset.filter(repair_request__employee__user=user)
        return queryset

    def get_permissions(self):
        if self.action in ["update_repair", "partial_update", "update"]:
            return [CanUpdateRepair()]
        if self.action in ["list", "retrieve"]:
            return [HasAnyAppPermission("view_repairs", "view_technician_repairs", "view_my_repair_requests")]
        return [IsAuthenticated()]

    @action(
        detail=True, methods=["post"], permission_classes=[CanUpdateRepair]
    )
    def update_repair(self, request, pk=None):
        """
        Complete repair by technician.

        POST /api/repair-logs/{id}/update_repair/
        """
        repair_log = self.get_object()
        notes = request.data.get("notes")
        parts_used = request.data.get("parts_used", "")

        if not notes:
            return Response(
                {"error": "notes is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            completed_log = RepairService.complete_repair(
                repair_log.repair_request.id,
                request.user,
                notes,
                parts_used,
            )

            serializer = RepairLogSerializer(completed_log)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


# =========================
# INVENTORY SESSION VIEWSET
# =========================
class InventorySessionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for inventory sessions.

    - list: Get all inventory sessions
    - create: Create session (HEAD_OFFICE only)
    """

    queryset = InventorySession.objects.all()
    serializer_class = InventorySessionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["branch"]
    ordering = ["-start_date"]

    def get_queryset(self):
        queryset = InventorySession.objects.select_related("branch", "created_by")
        if _deleted_only(self.request):
            return queryset.filter(is_deleted=True)
        if not _include_deleted(self.request):
            queryset = queryset.filter(is_deleted=False)
        return queryset

    def get_permissions(self):
        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
            "approve_head_office",
            "approve_branch",
            "close",
            "register_found_device",
        ]:
            if self.action == "approve_branch":
                return [HasAppPermission("approve_inventory")]
            return [CanCreateInventorySession()]
        if self.action in ["list", "retrieve"]:
            return [HasAnyAppPermission("view_inventory", "participate_inventory_verification")]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        """Create inventory session."""
        branch_id = request.data.get("branch_id")
        start_date = parse_datetime(request.data.get("start_date", "")) if request.data.get("start_date") else None
        end_date = parse_datetime(request.data.get("end_date", "")) if request.data.get("end_date") else None

        if not branch_id:
            return Response(
                {"error": "branch_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = InventoryService.create_inventory_session(
                branch_id, request.user, start_date=start_date, end_date=end_date
            )

            serializer = InventorySessionSerializer(session)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    def perform_update(self, serializer):
        session = serializer.save()
        AuditService.log_action(
            self.request.user,
            "INVENTORY_SESSION_UPDATED",
            "InventorySession",
            session.id,
            f"Session for {session.branch.name}",
        )

    def perform_destroy(self, instance):
        _soft_delete_instance(
            instance,
            self.request.user,
            "InventorySession",
            f"Session for {instance.branch.name}",
            self.request.data.get("reason", "") if hasattr(self.request, "data") else "",
        )

    def destroy(self, request, *args, **kwargs):
        session = self.get_object()
        activities = _inventory_delete_activities(session)
        if activities:
            return _activity_response("InventorySession", activities)
        self.perform_destroy(session)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[CanCreateInventorySession])
    def restore(self, request, pk=None):
        session = get_object_or_404(InventorySession.objects.all(), pk=pk)
        _restore_instance(session, request.user, "InventorySession", f"Session for {session.branch.name}")
        return Response(self.get_serializer(session).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["delete"], permission_classes=[CanCreateInventorySession])
    def permanent_delete(self, request, pk=None):
        session = get_object_or_404(InventorySession.objects.all(), pk=pk)
        activities = _inventory_delete_activities(session)
        if activities:
            return _activity_response("InventorySession", activities)
        session_id = session.id
        branch_name = session.branch.name
        session.delete()
        AuditService.log_action(
            request.user,
            "INVENTORYSESSION_PERMANENTLY_DELETED",
            "InventorySession",
            session_id,
            f"Session for {branch_name}",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[CanCreateInventorySession])
    def approve_head_office(self, request, pk=None):
        session = self.get_object()
        session.approved_by_head_office = True
        session.save()
        AuditService.log_action(
            request.user,
            "INVENTORY_APPROVED_HEAD_OFFICE",
            "InventorySession",
            session.id,
            f"Session for {session.branch.name}",
        )
        if session.branch.manager:
            _notify_user(
                session.branch.manager.user,
                f"Head Office completed final approval for {session.branch.name} inventory.",
            )
        return Response(self.get_serializer(session).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[CanCreateInventorySession])
    def close(self, request, pk=None):
        from django.utils import timezone
        session = self.get_object()
        session.end_date = timezone.now()
        session.save()
        AuditService.log_action(
            request.user,
            "INVENTORY_SESSION_CLOSED",
            "InventorySession",
            session.id,
            f"Session for {session.branch.name}",
        )
        return Response(self.get_serializer(session).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[CanCreateInventorySession])
    def register_found_device(self, request, pk=None):
        session = self.get_object()
        required_fields = ["device_type", "brand", "model", "serial_number", "company_tag"]
        missing_fields = [
            field for field in required_fields if not str(request.data.get(field, "")).strip()
        ]

        if missing_fields:
            return Response(
                {field: ["This field is required."] for field in missing_fields},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serial_number = request.data["serial_number"].strip()
        company_tag = request.data["company_tag"].strip()

        if Device.objects.filter(serial_number__iexact=serial_number).exists():
            return Response(
                {"serial_number": "A device with this serial number is already registered."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if Device.objects.filter(company_tag__iexact=company_tag).exists():
            return Response(
                {"company_tag": "A device with this company tag is already registered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            device = Device.objects.create(
                device_type=request.data["device_type"].strip(),
                brand=request.data["brand"].strip(),
                model=request.data["model"].strip(),
                serial_number=serial_number,
                company_tag=company_tag,
                status="AVAILABLE",
                assigned_branch=session.branch,
                location_type="BRANCH",
                current_location=session.branch.name,
                condition_notes=request.data.get("condition_notes", "").strip(),
            )
            item = InventoryItem.objects.create(
                session=session,
                device=device,
                status="EXTRA",
                comment=request.data.get("comment", "").strip(),
            )
            AuditService.log_action(
                request.user,
                "INVENTORY_FOUND_DEVICE_REGISTERED",
                "InventoryItem",
                item.id,
                f"Found device {device.company_tag} registered during {session.branch.name} inventory.",
            )
            if session.branch.manager:
                _notify_user(
                    session.branch.manager.user,
                    f"Found device {device.company_tag} was registered during {session.branch.name} inventory.",
                )

        return Response(InventoryItemSerializer(item).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[CanVerifyInventory])
    def approve_branch(self, request, pk=None):
        session = self.get_object()
        session.approved_by_branch = True
        session.save(update_fields=["approved_by_branch"])
        AuditService.log_action(
            request.user,
            "INVENTORY_APPROVED_BRANCH",
            "InventorySession",
            session.id,
            f"Session for {session.branch.name}",
        )
        _notify_head_office(
            f"{session.branch.name} inventory was approved by the Branch Manager and is ready for final approval."
        )
        return Response(self.get_serializer(session).data, status=status.HTTP_200_OK)


# =========================
# INVENTORY ITEM VIEWSET
# =========================
class InventoryItemViewSet(viewsets.ModelViewSet):
    """
    API endpoint for inventory items.

    - list: Get all inventory items
    - mark_verified: Mark as verified (BRANCH_MANAGER only)
    - mark_missing: Mark as missing (BRANCH_MANAGER only)
    """

    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["session", "status"]
    search_fields = ["device__company_tag"]

    def get_permissions(self):
        if self.action in [
            "mark_verified",
            "mark_pending",
            "mark_missing",
            "mark_extra",
            "mark_in_repair",
            "return_head_office",
            "update",
            "partial_update",
        ]:
            return [CanVerifyInventory()]
        if self.action in ["list", "retrieve"]:
            return [HasAnyAppPermission("view_inventory", "participate_inventory_verification")]
        return [IsAuthenticated()]

    @action(detail=True, methods=["post"], permission_classes=[CanVerifyInventory])
    def mark_pending(self, request, pk=None):
        item = self.get_object()
        comment = request.data.get("comment", "")
        item.status = "PENDING"
        item.comment = comment
        item.save(update_fields=["status", "comment"])
        AuditService.log_action(
            request.user,
            "INVENTORY_PENDING",
            "InventoryItem",
            item.id,
            f"Device {item.device.company_tag} marked pending",
        )
        return Response(self.get_serializer(item).data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[CanVerifyInventory],
    )
    def mark_verified(self, request, pk=None):
        """
        Mark inventory item as verified.

        POST /api/inventory-items/{id}/mark_verified/
        """
        item = self.get_object()
        comment = request.data.get("comment", "")

        try:
            InventoryService.mark_item_verified(item.id, request.user, comment)

            updated_item = InventoryItem.objects.get(id=item.id)
            serializer = InventoryItemSerializer(updated_item)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[CanVerifyInventory],
    )
    def mark_missing(self, request, pk=None):
        """
        Mark inventory item as missing.

        POST /api/inventory-items/{id}/mark_missing/
        """
        item = self.get_object()
        comment = request.data.get("comment", "")

        try:
            InventoryService.mark_item_missing(
                item.id, request.user, comment
            )

            updated_item = InventoryItem.objects.get(id=item.id)
            serializer = InventoryItemSerializer(updated_item)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[CanVerifyInventory],
    )
    def mark_extra(self, request, pk=None):
        item = self.get_object()
        comment = request.data.get("comment", "")
        item.status = "EXTRA"
        item.comment = comment
        item.save(update_fields=["status", "comment"])
        AuditService.log_action(
            request.user,
            "INVENTORY_EXTRA",
            "InventoryItem",
            item.id,
            f"Device {item.device.company_tag} marked extra",
        )
        if item.session.branch.manager:
            _notify_user(
                item.session.branch.manager.user,
                f"Found device {item.device.company_tag} was registered during {item.session.branch.name} inventory.",
            )
        return Response(self.get_serializer(item).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOffice])
    def mark_in_repair(self, request, pk=None):
        item = self.get_object()
        comment = request.data.get("comment", "")
        item.status = "IN_REPAIR"
        item.comment = comment
        item.device.status = "IN_REPAIR"
        item.device.save(update_fields=["status"])
        item.save(update_fields=["status", "comment"])
        AuditService.log_action(
            request.user,
            "INVENTORY_IN_REPAIR",
            "InventoryItem",
            item.id,
            f"Device {item.device.company_tag} marked in repair",
        )
        if item.session.branch.manager:
            _notify_user(
                item.session.branch.manager.user,
                f"Device {item.device.company_tag} was marked in repair during {item.session.branch.name} inventory.",
            )
        return Response(self.get_serializer(item).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOffice])
    def return_head_office(self, request, pk=None):
        item = self.get_object()
        comment = request.data.get("comment", "")
        device = item.device
        item.status = "RETURNED_HEAD_OFFICE"
        item.comment = comment
        device.status = "AVAILABLE"
        device.assigned_employee = None
        device.assigned_branch = None
        device.location_type = "HEAD_OFFICE"
        device.current_location = "Head Office"
        device.save()
        item.save(update_fields=["status", "comment"])
        AuditService.log_action(
            request.user,
            "INVENTORY_RETURNED_HEAD_OFFICE",
            "InventoryItem",
            item.id,
            f"Device {device.company_tag} returned to Head Office inventory",
        )
        if item.session.branch.manager:
            _notify_user(
                item.session.branch.manager.user,
                f"Device {device.company_tag} was returned to Head Office from {item.session.branch.name} inventory.",
            )
        return Response(self.get_serializer(item).data, status=status.HTTP_200_OK)


# =========================
# NOTIFICATION VIEWSET
# =========================
class NotificationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for notifications.

    - list: Get user's notifications
    - mark_as_read: Mark notification as read
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Return only current user's notifications."""
        return Notification.objects.filter(user=self.request.user)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def mark_as_read(self, request, pk=None):
        """Mark notification as read."""
        notification = self.get_object()
        notification.is_read = True
        notification.save()

        serializer = NotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)


# =========================
# AUDIT LOG VIEWSET
# =========================
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for audit logs (read-only).

    - list: Get all audit logs (HEAD_OFFICE only)
    - retrieve: Get audit log details (HEAD_OFFICE only)
    """

    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [HasAppPermission("view_audit_logs")]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["action", "model_name"]
    search_fields = ["action", "details"]
    ordering = ["-timestamp"]


def _get_dashboard_url(role):
    role_dashboard_map = {
        "HEAD_OFFICE": "head_office_dashboard",
        "BRANCH_MANAGER": "branch_manager_dashboard",
        "EMPLOYEE": "employee_dashboard",
        "TECHNICIAN": "technician_dashboard",
    }
    return reverse(role_dashboard_map.get(role, "login"))


def _get_user_dashboard_url(user):
    dashboard_permissions = [
        ("view_head_office_dashboard", "head_office_dashboard"),
        ("view_branch_devices", "branch_manager_dashboard"),
        ("view_technician_repairs", "technician_dashboard"),
        ("view_my_devices", "employee_dashboard"),
    ]
    for permission, url_name in dashboard_permissions:
        if user_has_permission(user, permission):
            return reverse(url_name)
    return _get_dashboard_url(user.role)


def _employee_for_user(user):
    return Employee.objects.select_related("branch", "department").filter(user=user).first()


def _attach_repair_activity(repairs):
    repair_list = list(repairs)
    repair_ids = [repair.id for repair in repair_list]
    logs = {
        log.repair_request_id: log
        for log in RepairLog.objects.select_related("technician", "repair_request").filter(
            repair_request_id__in=repair_ids
        )
    }
    log_ids = [log.id for log in logs.values()]
    audit_logs = AuditLog.objects.select_related("user").filter(
        Q(model_name="RepairRequest", object_id__in=repair_ids)
        | Q(model_name="RepairLog", object_id__in=log_ids)
    ).order_by("timestamp")

    activity_by_repair = {repair_id: [] for repair_id in repair_ids}
    log_to_repair = {log.id: repair_id for repair_id, log in logs.items()}
    for audit in audit_logs:
        repair_id = audit.object_id
        if audit.model_name == "RepairLog":
            repair_id = log_to_repair.get(audit.object_id)
        if repair_id in activity_by_repair:
            activity_by_repair[repair_id].append(audit)

    for repair in repair_list:
        repair.activity_logs = activity_by_repair.get(repair.id, [])
        repair.repair_log = logs.get(repair.id)
    return repair_list


def _device_audit_timeline(device):
    assignments = list(
        DeviceAssignment.objects.select_related(
            "employee", "employee__branch", "branch", "assigned_by", "received_by"
        )
        .filter(device=device)
        .order_by("assigned_date")
    )
    repairs = list(
        RepairRequest.objects.select_related(
            "employee", "approved_by", "repairlog", "repairlog__technician"
        )
        .filter(device=device)
        .order_by("request_date")
    )
    inventory_items = list(
        InventoryItem.objects.select_related("session", "session__branch", "session__created_by")
        .filter(device=device)
        .order_by("session__start_date")
    )
    location_events = list(
        DeviceLocationHistory.objects.select_related("updated_by")
        .filter(device=device)
        .order_by("timestamp")
    )

    assignment_ids = [assignment.id for assignment in assignments]
    repair_ids = [repair.id for repair in repairs]
    repair_log_ids = [
        repair.repairlog.id
        for repair in repairs
        if hasattr(repair, "repairlog") and repair.repairlog
    ]
    inventory_item_ids = [item.id for item in inventory_items]

    audit_logs = list(
        AuditLog.objects.select_related("user")
        .filter(
            Q(model_name="Device", object_id=device.id)
            | Q(model_name="DeviceAssignment", object_id__in=assignment_ids)
            | Q(model_name="RepairRequest", object_id__in=repair_ids)
            | Q(model_name="RepairLog", object_id__in=repair_log_ids)
            | Q(model_name="InventoryItem", object_id__in=inventory_item_ids)
            | Q(details__icontains=device.company_tag)
            | Q(details__icontains=device.serial_number)
        )
        .order_by("timestamp")
    )

    timeline = [
        {
            "timestamp": device.registered_at,
            "title": "Device registered",
            "description": f"{device.device_type} {device.brand} {device.model} was added to the system.",
            "badge": "Registered",
            "user": "System",
            "details": [
                ("Company tag", device.company_tag),
                ("Serial number", device.serial_number),
                ("Initial status", device.get_status_display()),
                ("Initial location", device.current_location),
            ],
        }
    ]

    for assignment in assignments:
        timeline.append(
            {
                "timestamp": assignment.assigned_date,
                "title": "Device assigned",
                "description": f"Assigned to {assignment.employee.full_name if assignment.employee else 'Unknown employee'}.",
                "badge": "Assignment",
                "user": assignment.assigned_by.username if assignment.assigned_by else "System",
                "details": [
                    ("Employee", assignment.employee.full_name if assignment.employee else "-"),
                    ("Branch", assignment.branch.name if assignment.branch else "-"),
                    ("Assigned by", assignment.assigned_by.username if assignment.assigned_by else "-"),
                    ("Condition on issue", assignment.condition_on_issue or "-"),
                ],
            }
        )
        if assignment.returned_date:
            timeline.append(
                {
                    "timestamp": assignment.returned_date,
                    "title": "Device returned",
                    "description": f"Returned by {assignment.employee.full_name if assignment.employee else 'Unknown employee'}.",
                    "badge": "Return",
                    "user": assignment.received_by.username if assignment.received_by else "System",
                    "details": [
                        ("Received by", assignment.received_by.username if assignment.received_by else "-"),
                        ("Condition on return", assignment.condition_on_return or "-"),
                    ],
                }
            )

    for repair in repairs:
        repair_log = repair.repairlog if hasattr(repair, "repairlog") else None
        timeline.append(
            {
                "timestamp": repair.request_date,
                "title": "Repair requested",
                "description": repair.issue_description,
                "badge": repair.status,
                "user": repair.employee.full_name if repair.employee else "System",
                "details": [
                    ("Employee", repair.employee.full_name if repair.employee else "-"),
                    ("Priority", repair.priority),
                    ("Approved by", repair.approved_by.username if repair.approved_by else "-"),
                    ("Technician", repair_log.technician.username if repair_log and repair_log.technician else "-"),
                    ("Repair notes", repair_log.notes if repair_log else "-"),
                    ("Parts used", repair_log.parts_used if repair_log and repair_log.parts_used else "-"),
                ],
            }
        )
        if repair_log:
            timeline.append(
                {
                    "timestamp": repair_log.start_date,
                    "title": "Repair work started",
                    "description": repair_log.notes or repair.issue_description,
                    "badge": "Repair",
                    "user": repair_log.technician.username if repair_log.technician else "System",
                    "details": [
                        ("Technician", repair_log.technician.username if repair_log.technician else "-"),
                        ("Parts used", repair_log.parts_used or "-"),
                    ],
                }
            )
            if repair_log.completed_date:
                timeline.append(
                    {
                        "timestamp": repair_log.completed_date,
                        "title": "Repair completed",
                        "description": repair_log.notes or "Repair completed.",
                        "badge": "Completed",
                        "user": repair_log.technician.username if repair_log.technician else "System",
                        "details": [
                            ("Final device status", device.get_status_display()),
                            ("Parts used", repair_log.parts_used or "-"),
                        ],
                    }
                )

    for item in inventory_items:
        timeline.append(
            {
                "timestamp": item.session.start_date,
                "title": "Inventory verification",
                "description": item.comment or f"Inventory status recorded as {item.status}.",
                "badge": item.status,
                "user": item.session.created_by.username if item.session.created_by else "System",
                "details": [
                    ("Branch", item.session.branch.name if item.session.branch else "-"),
                    ("Inventory status", item.get_status_display()),
                    ("Comment", item.comment or "-"),
                ],
            }
        )

    for event in location_events:
        timeline.append(
            {
                "timestamp": event.timestamp,
                "title": "Location updated",
                "description": event.location,
                "badge": event.action.replace("_", " ").title(),
                "user": event.updated_by.username if event.updated_by else "System",
                "details": [
                    ("Location type", event.get_location_type_display()),
                    ("Device status", event.status or "-"),
                    ("Action", event.action),
                    ("Notes", event.notes or "-"),
                ],
            }
        )

    for audit in audit_logs:
        timeline.append(
            {
                "timestamp": audit.timestamp,
                "title": audit.action.replace("_", " ").title(),
                "description": audit.details or "-",
                "badge": "Audit",
                "user": audit.user.username if audit.user else "System",
                "details": [
                    ("Model", audit.model_name),
                    ("Object ID", audit.object_id or "-"),
                ],
            }
        )

    return sorted(timeline, key=lambda item: item["timestamp"] or timezone.now())


def _device_audit_context(request):
    query = request.GET.get("q", "").strip()
    devices = Device.objects.select_related("assigned_employee", "assigned_branch").none()
    selected_device = None
    timeline = []
    assignments = DeviceAssignment.objects.none()
    repairs = RepairRequest.objects.none()
    audit_logs = AuditLog.objects.none()

    if query:
        devices = (
            Device.objects.select_related("assigned_employee", "assigned_branch")
            .filter(
                Q(company_tag__icontains=query)
                | Q(serial_number__icontains=query)
                | Q(assigned_employee__full_name__icontains=query)
                | Q(assignments__employee__full_name__icontains=query)
            )
            .distinct()
            .order_by("company_tag")
        )
        selected_device_id = request.GET.get("device")
        if selected_device_id:
            selected_device = get_object_or_404(devices, id=selected_device_id)
        else:
            exact_match = devices.filter(Q(company_tag__iexact=query) | Q(serial_number__iexact=query)).first()
            selected_device = exact_match or (devices.first() if devices.count() == 1 else None)

    if selected_device:
        timeline = _device_audit_timeline(selected_device)
        assignments = selected_device.assignments.select_related(
            "employee", "branch", "assigned_by", "received_by"
        ).order_by("-assigned_date")
        repairs = RepairRequest.objects.select_related(
            "employee", "approved_by", "repairlog", "repairlog__technician"
        ).filter(device=selected_device).order_by("-request_date")
        audit_logs = AuditLog.objects.select_related("user").filter(
            Q(model_name="Device", object_id=selected_device.id)
            | Q(details__icontains=selected_device.company_tag)
            | Q(details__icontains=selected_device.serial_number)
        ).order_by("-timestamp")

    return {
        "query": query,
        "matching_devices": devices,
        "selected_device": selected_device,
        "timeline": timeline,
        "assignments": assignments,
        "repairs": repairs,
        "audit_logs": audit_logs,
    }


def home_view(request):
    """Root view: redirect to login if not authenticated, dashboard if authenticated."""
    if request.user.is_authenticated:
        return redirect(_get_user_dashboard_url(request.user))
    return redirect("login")


def login_view(request):
    if request.method == "POST":
        username_or_email = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # Try to authenticate with username first
        user = authenticate(request, username=username_or_email, password=password)

        # If that fails, try with email
        if user is None:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass

        if user is not None and user.is_active:
            login(request, user)
            messages.success(request, "Login successful.")
            return redirect(_get_dashboard_url(user.role))

        inactive_user = User.objects.filter(
            Q(username=username_or_email) | Q(email=username_or_email),
            is_active=False,
        ).first()
        if inactive_user:
            messages.error(request, DEACTIVATED_ACCOUNT_MESSAGE)
            return render(request, "Auth/login.html", {"username": username_or_email})

        messages.error(request, "Invalid username or password.")
        return render(request, "Auth/login.html", {"username": username_or_email})

    if request.GET.get("message"):
        messages.error(request, request.GET["message"])
    return render(request, "Auth/login.html")


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Logout successful.")
    return redirect("login")


@login_required
def dashboard_redirect(request):
    return redirect(_get_user_dashboard_url(request.user))


@login_required
def profile_details(request):
    employee = _employee_for_user(request.user)
    if request.method == "POST":
        request.user.email = request.POST.get("email", request.user.email).strip()
        request.user.username = request.POST.get("username", request.user.username).strip()
        request.user.save(update_fields=["username", "email"])
        if employee:
            employee.full_name = request.POST.get("full_name", employee.full_name).strip()
            employee.position = request.POST.get("position", employee.position).strip()
            employee.save(update_fields=["full_name", "position"])
        messages.success(request, "Profile updated successfully.")
        return redirect("profile_details")
    return render(request, "ProfileDetails.html", {"employee": employee})


@login_required
def account_settings(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password", "")
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")
        request.user.username = request.POST.get("username", request.user.username).strip()
        request.user.email = request.POST.get("email", request.user.email).strip()
        password_changed = False
        if new_password or confirm_password:
            if not request.user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
                return redirect("account_settings")
            if new_password != confirm_password:
                messages.error(request, "New password and confirm password must match.")
                return redirect("account_settings")
            request.user.set_password(new_password)
            request.user.must_change_password = False
            password_changed = True
        request.user.save()
        if password_changed:
            logout(request)
            messages.success(request, "Password changed successfully. Please login again using your new password.")
            return redirect("login")
        messages.success(request, "Account settings updated successfully.")
        return redirect("account_settings")
    return render(request, "AccountSettings.html")


@login_required
def first_login_password_change(request):
    if not request.user.must_change_password:
        return redirect("dashboard_redirect")
    if request.method == "POST":
        current_password = request.POST.get("current_password", "")
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")
        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
        elif new_password != confirm_password:
            messages.error(request, "New password and confirm password must match.")
        elif request.user.check_password(new_password):
            messages.error(request, "The new password cannot be the same as the default password.")
        else:
            request.user.set_password(new_password)
            request.user.must_change_password = False
            request.user.save(update_fields=["password", "must_change_password"])
            logout(request)
            messages.success(request, "Password changed successfully. Please login again using your new password.")
            return redirect("login")
    return render(request, "FirstLoginPasswordChange.html")


@login_required
@permission_required("view_head_office_dashboard")
def head_office_dashboard(request):
    """Head Office Dashboard with complete system overview."""
    from django.db.models import Count, Q
    
    # Device Statistics
    total_devices = Device.objects.filter(is_deleted=False).count()
    assigned_devices = Device.objects.filter(status='ASSIGNED', is_deleted=False).count()
    available_devices = Device.objects.filter(status='AVAILABLE', is_deleted=False).count()
    in_repair_devices = Device.objects.filter(status='IN_REPAIR', is_deleted=False).count()
    missing_devices = Device.objects.filter(status='MISSING', is_deleted=False).count()
    
    # Calculate percentages
    percentage_assigned = round((assigned_devices / total_devices * 100) if total_devices > 0 else 0, 1)
    
    # Employee Statistics
    total_employees = Employee.objects.filter(is_deleted=False).count()
    active_employees = Employee.objects.filter(status='ACTIVE', is_deleted=False).count()
    inactive_employees = Employee.objects.filter(status='INACTIVE', is_deleted=False).count()
    exited_employees = Employee.objects.filter(status='EXITED', is_deleted=False).count()
    
    # Branch Statistics
    total_branches = Branch.objects.filter(is_deleted=False).count()
    
    # Repair Statistics
    pending_repairs = RepairRequest.objects.filter(status='PENDING').count()
    approved_repairs = RepairRequest.objects.filter(status='APPROVED').count()
    completed_repairs = RepairRequest.objects.filter(status='COMPLETED').count()
    
    # Recent Activities
    recent_audits = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]
    
    # Recent Repair Requests
    recent_repairs = RepairRequest.objects.select_related('device', 'employee', 'approved_by').order_by('-request_date')[:5]
    
    # Device Status Distribution for Charts
    device_status_data = Device.objects.filter(is_deleted=False).values('status').annotate(count=Count('id'))
    
    # Device Type Distribution
    device_type_data = Device.objects.filter(is_deleted=False).values('device_type').annotate(count=Count('id'))
    
    # Devices per Branch
    branch_device_data = Device.objects.filter(is_deleted=False).values('assigned_branch__name').annotate(count=Count('id')).exclude(assigned_branch__isnull=True)
    
    context = {
        # Key Metrics
        'total_devices': total_devices,
        'assigned_devices': assigned_devices,
        'available_devices': available_devices,
        'in_repair_devices': in_repair_devices,
        'missing_devices': missing_devices,
        'percentage_assigned': percentage_assigned,
        
        # Employee Metrics
        'total_employees': total_employees,
        'active_employees': active_employees,
        'inactive_employees': inactive_employees,
        'exited_employees': exited_employees,
        
        # Branch Metrics
        'total_branches': total_branches,
        
        # Repair Metrics
        'pending_repairs': pending_repairs,
        'approved_repairs': approved_repairs,
        'completed_repairs': completed_repairs,
        
        # Lists
        'recent_audits': recent_audits,
        'recent_repairs': recent_repairs,
        
        # Chart Data
        'device_status_data': list(device_status_data),
        'device_type_data': list(device_type_data),
        'branch_device_data': list(branch_device_data),
    }
    
    return render(request, "HeadOffice/Dashboard.html", context)


@login_required
@permission_required("view_branch_devices")
def branch_manager_dashboard(request):
    employee = _employee_for_user(request.user)
    branch = employee.branch if employee else None
    devices = Device.objects.filter(assigned_branch=branch, is_deleted=False) if branch else Device.objects.none()
    employees = Employee.objects.filter(branch=branch, is_deleted=False) if branch else Employee.objects.none()
    repairs = RepairRequest.objects.select_related("device", "employee").filter(
        device__assigned_branch=branch
    ) if branch else RepairRequest.objects.none()
    recent_audits = AuditLog.objects.select_related("user").filter(
        Q(model_name="Device", object_id__in=devices.values("id"))
        | Q(model_name="RepairRequest", object_id__in=repairs.values("id"))
        | Q(details__icontains=branch.name if branch else "")
    ).order_by("-timestamp")[:8] if branch else AuditLog.objects.none()
    status_data = list(devices.values("status").annotate(count=Count("id")).order_by("status"))
    repair_data = list(repairs.values("status").annotate(count=Count("id")).order_by("status"))
    context = {
        "branch": branch,
        "total_devices": devices.count(),
        "assigned_devices": devices.filter(status="ASSIGNED").count(),
        "under_repair_devices": devices.filter(status="IN_REPAIR").count(),
        "completed_repairs": repairs.filter(status="COMPLETED").count(),
        "employee_count": employees.count(),
        "missing_count": devices.filter(status="MISSING").count(),
        "repair_count": devices.filter(status="IN_REPAIR").count(),
        "recent_audits": recent_audits,
        "recent_repairs": repairs.order_by("-request_date")[:5],
        "device_status_data": status_data,
        "repair_status_data": repair_data,
        "sessions": InventorySession.objects.filter(branch=branch).order_by("-start_date")[:5] if branch else [],
    }
    return render(request, "BranchManage/Dashboard.html", context)


@login_required
@permission_required("view_my_devices")
def employee_dashboard(request):
    employee = Employee.objects.filter(user=request.user).first()
    devices = Device.objects.filter(assigned_employee=employee, is_deleted=False) if employee else Device.objects.none()
    repairs = RepairRequest.objects.filter(employee=employee) if employee else RepairRequest.objects.none()
    context = {
        "employee": employee,
        "devices": devices,
        "repairs": repairs.select_related("device") if employee else repairs,
        "pending_repairs": repairs.filter(status="PENDING").count() if employee else 0,
        "approved_repairs": repairs.filter(status="APPROVED").count() if employee else 0,
        "in_progress_repairs": repairs.filter(status="IN_PROGRESS").count() if employee else 0,
        "completed_repairs": repairs.filter(status="COMPLETED").count() if employee else 0,
    }
    return render(request, "Employee/Dashboard.html", context)


@login_required
@permission_required("view_technician_repairs")
def technician_dashboard(request):
    repairs = RepairRequest.objects.select_related("device", "employee").filter(
        repairlog__technician=request.user
    )
    context = {
        "approved_repairs": repairs.filter(status="APPROVED"),
        "in_progress_repairs": repairs.filter(status="IN_PROGRESS"),
        "completed_today": repairs.filter(
            status="COMPLETED",
            repairlog__completed_date__date=timezone.localdate(),
        ).count(),
        "completed_repairs": repairs.filter(status="COMPLETED").order_by("-request_date")[:5],
    }
    return render(request, "Technician/Dashboard.html", context)


@login_required
@permission_required("view_technician_repairs")
def technician_repairs(request):
    repairs = RepairRequest.objects.select_related(
        "device", "device__assigned_branch", "device__assigned_employee", "employee"
    ).filter(status="APPROVED", repairlog__technician=request.user).order_by("-request_date")
    return render(request, "Technician/Repairs.html", {"repairs": repairs})


@login_required
@permission_required("update_repair_progress")
def technician_in_progress_repairs(request):
    repairs = RepairRequest.objects.select_related(
        "device", "device__assigned_branch", "employee"
    ).filter(status="IN_PROGRESS", repairlog__technician=request.user).order_by("-request_date")
    return render(request, "Technician/InProgressRepairs.html", {"repairs": repairs})


@login_required
@permission_required("mark_repair_completed")
def technician_completed_repairs(request):
    repair_logs = RepairLog.objects.select_related(
        "repair_request", "repair_request__device", "repair_request__employee", "technician"
    ).filter(repair_request__status="COMPLETED", technician=request.user).order_by("-completed_date", "-start_date")
    return render(request, "Technician/CompletedRepairs.html", {"repair_logs": repair_logs})


@login_required
@permission_required("diagnose_device_issue")
def technician_device_lookup(request):
    devices = Device.objects.select_related("assigned_employee", "assigned_branch").filter(
        repairrequest__repairlog__technician=request.user
    ).distinct().order_by("company_tag")
    return render(request, "Technician/DeviceLookup.html", {"devices": devices})


@login_required
@permission_required("view_technician_repairs")
def technician_repair_history(request):
    repair_logs = RepairLog.objects.select_related(
        "repair_request", "repair_request__device", "repair_request__employee", "technician"
    ).filter(technician=request.user).order_by("-start_date")
    return render(request, "Technician/RepairHistory.html", {"repair_logs": repair_logs})


@login_required
@permission_required("view_my_devices")
def employee_my_devices(request):
    employee = _employee_for_user(request.user)
    devices = Device.objects.select_related("assigned_branch").filter(assigned_employee=employee, is_deleted=False) if employee else Device.objects.none()
    return render(request, "Employee/MyDevices.html", {"employee": employee, "devices": devices})


@login_required
@permission_required("submit_repair_request")
def employee_request_repair(request):
    employee = _employee_for_user(request.user)
    devices = Device.objects.filter(assigned_employee=employee, is_deleted=False).exclude(status__in=["RETIRED", "MISSING", "DECOMMISSIONED"]) if employee else Device.objects.none()
    if employee:
        open_device_ids = RepairRequest.objects.filter(
            employee=employee,
            status__in=["PENDING", "APPROVED", "IN_PROGRESS"],
        ).values_list("device_id", flat=True)
        devices = devices.exclude(id__in=open_device_ids)
    return render(request, "Employee/RequestRepair.html", {"employee": employee, "devices": devices})


@login_required
@permission_required("view_my_repair_requests")
def employee_repair_requests(request):
    employee = _employee_for_user(request.user)
    repairs = RepairRequest.objects.select_related("device", "approved_by", "employee").filter(employee=employee).order_by("-request_date") if employee else RepairRequest.objects.none()
    repairs = _attach_repair_activity(repairs) if employee else repairs
    return render(request, "Employee/RepairRequests.html", {"employee": employee, "repairs": repairs})


# =========================
# HEAD OFFICE MANAGEMENT VIEWS
# =========================

@login_required
@permission_required("view_employee")
def head_office_employees(request):
    """Employee management view."""
    show_deleted = request.GET.get("deleted") == "1"
    employees = Employee.objects.select_related(
        'user', 'branch', 'department'
    ).prefetch_related('device_set').filter(is_deleted=show_deleted)
    branches = Branch.objects.filter(is_deleted=False)
    departments = Department.objects.filter(is_deleted=False)
    users = User.objects.exclude(role="HEAD_OFFICE")
    role_options = Role.objects.exclude(code="HEAD_OFFICE").order_by("is_system", "name")
    
    context = {
        'employees': employees,
        'branches': branches,
        'departments': departments,
        'users': users,
        'role_options': role_options,
        'statuses': Employee._meta.get_field('status').choices,
        'show_deleted': show_deleted,
    }
    return render(request, "HeadOffice/Employee.html", context)


@login_required
@permission_required("view_branch")
def head_office_branches(request):
    """Branch and department management view."""
    show_deleted = request.GET.get("deleted") == "1"
    branches = Branch.objects.prefetch_related(
        'departments',
        'employees',
        'employees__device_set',
        'employees__department',
    ).filter(is_deleted=show_deleted)
    context = {
        'branches': branches,
        'show_deleted': show_deleted,
    }
    return render(request, "HeadOffice/Branches.html", context)


@login_required
@permission_required("view_department")
def head_office_departments(request):
    """Global department registration view."""
    show_deleted = request.GET.get("deleted") == "1"
    department_names = (
        Department.objects.filter(is_deleted=show_deleted)
        .values("name")
        .annotate(branch_count=Count("branch", distinct=True), first_id=Min("id"))
        .order_by("name")
    )
    return render(
        request,
        "HeadOffice/Departments.html",
        {
            "department_names": department_names,
            "branch_count": Branch.objects.filter(is_deleted=False).count(),
            "show_deleted": show_deleted,
        },
    )


@login_required
@permission_required("view_device")
def head_office_devices(request):
    """Device management view."""
    show_deleted = request.GET.get("deleted") == "1"
    device_scope = request.GET.get("scope", "active")
    devices = Device.objects.select_related('assigned_employee', 'assigned_branch').filter(is_deleted=show_deleted)
    if device_scope == "decommissioned":
        devices = devices.filter(status="DECOMMISSIONED")
    elif device_scope == "active":
        devices = devices.exclude(status="DECOMMISSIONED")
    branches = Branch.objects.filter(is_deleted=False)
    employees = Employee.objects.select_related('branch').filter(status='ACTIVE', is_deleted=False)
    statuses = Device._meta.get_field('status').choices
    location_types = Device._meta.get_field('location_type').choices
    device_types = Device.objects.values_list('device_type', flat=True).distinct()
    device_type_counts = (
        Device.objects.filter(is_deleted=show_deleted)
        .values('device_type')
        .annotate(count=Count('id'))
        .order_by('device_type')
    )
    
    context = {
        'devices': devices,
        'branches': branches,
        'employees': employees,
        'statuses': statuses,
        'location_types': location_types,
        'device_types': device_types,
        'device_type_counts': device_type_counts,
        'show_deleted': show_deleted,
        'device_scope': device_scope,
    }
    return render(request, "HeadOffice/Devices.html", context)


@login_required
@permission_required("view_assignment")
def head_office_assignments(request):
    """Device assignment management view."""
    assignments = DeviceAssignment.objects.select_related(
        'device', 'employee', 'branch', 'assigned_by', 'received_by'
    ).all().order_by('-assigned_date')
    
    active_assignments = assignments.filter(returned_date__isnull=True)
    returned_assignments = assignments.filter(returned_date__isnull=False)
    
    employees = Employee.objects.filter(status='ACTIVE')
    available_devices = Device.objects.select_related('assigned_branch').filter(
        Q(status='AVAILABLE')
        | Q(status__in=['REPAIRED', 'COMPLETED'], assigned_employee__isnull=True)
    ).filter(is_deleted=False).exclude(status="DECOMMISSIONED")
    branches = Branch.objects.all()
    
    context = {
        'assignments': assignments,
        'active_assignments': active_assignments,
        'returned_assignments': returned_assignments,
        'employees': employees,
        'available_devices': available_devices,
        'branches': branches,
    }
    return render(request, "HeadOffice/Assignments.html", context)


@login_required
@permission_required("view_repairs")
def head_office_repairs(request):
    """Repair request management view."""
    repairs = RepairRequest.objects.select_related(
        'device', 'employee', 'approved_by'
    ).all().order_by('-request_date')
    repairs = _attach_repair_activity(repairs)
    
    repairs_by_status = {
        'PENDING': [repair for repair in repairs if repair.status == 'PENDING'],
        'APPROVED': [repair for repair in repairs if repair.status == 'APPROVED'],
        'REJECTED': [repair for repair in repairs if repair.status == 'REJECTED'],
        'IN_PROGRESS': [repair for repair in repairs if repair.status == 'IN_PROGRESS'],
        'COMPLETED': [repair for repair in repairs if repair.status == 'COMPLETED'],
    }
    
    context = {
        'repairs': repairs,
        'repairs_by_status': repairs_by_status,
        'statuses': RepairRequest._meta.get_field('status').choices,
        'devices': Device.objects.select_related('assigned_employee').filter(is_deleted=False).exclude(assigned_employee__isnull=True).exclude(status="DECOMMISSIONED"),
        'employees': Employee.objects.filter(status='ACTIVE'),
        'technicians': User.objects.select_related('employee').filter(role='TECHNICIAN', is_active=True).order_by('employee__full_name', 'username'),
    }
    return render(request, "HeadOffice/RequestRepairs.html", context)


@login_required
@permission_required("view_device_audit")
def head_office_audit_device(request):
    """Full lifecycle audit view for a device."""
    return render(request, "HeadOffice/AuditDevice.html", _device_audit_context(request))


@login_required
@permission_required("view_inventory")
def head_office_inventory(request):
    """Inventory management view."""
    show_deleted = request.GET.get("deleted") == "1"
    inventory_sessions = InventorySession.objects.select_related(
        'branch', 'created_by'
    ).prefetch_related('items', 'items__device', 'items__device__assigned_employee').filter(is_deleted=show_deleted).order_by('-start_date')
    
    branches = Branch.objects.filter(is_deleted=False)
    
    context = {
        'inventory_sessions': inventory_sessions,
        'branches': branches,
        'show_deleted': show_deleted,
    }
    return render(request, "HeadOffice/Inventory.html", context)


@login_required
@permission_required("view_inventory")
def head_office_inventory_detail(request, session_id):
    """Dedicated inventory session details page."""
    session = get_object_or_404(InventorySession.objects.select_related("branch", "created_by").prefetch_related(
        "items",
        "items__device",
        "items__device__assigned_employee",
        "items__device__assigned_branch",
    ), id=session_id)
    items = list(session.items.select_related(
        "device", "device__assigned_employee", "device__assigned_branch"
    ).all().order_by("device__company_tag"))

    device_ids = [item.device_id for item in items]
    repair_requests = RepairRequest.objects.filter(device_id__in=device_ids).select_related(
        "approved_by"
    ).prefetch_related("repairlog").order_by("-request_date")

    latest_repairs = {}
    for repair_request in repair_requests:
        if repair_request.device_id not in latest_repairs:
            latest_repairs[repair_request.device_id] = repair_request

    for item in items:
        item.latest_repair = latest_repairs.get(item.device_id)
        item.repair_started = bool(item.latest_repair and item.latest_repair.status in ("APPROVED", "IN_PROGRESS"))
        if item.latest_repair and hasattr(item.latest_repair, "repairlog") and item.latest_repair.repairlog.technician:
            item.repair_technician = getattr(item.latest_repair.repairlog.technician, 'username', None)
        else:
            item.repair_technician = None

    departments = Department.objects.filter(branch=session.branch).order_by("name")
    department_groups = []
    grouped_item_ids = set()

    for department in departments:
        department_items = [
            item for item in items
            if item.device.assigned_employee and item.device.assigned_employee.department_id == department.id
        ]
        grouped_item_ids.update(item.id for item in department_items)
        department_groups.append(
            {
                "name": department.name,
                "items": department_items,
                "count": len(department_items),
            }
        )

    other_items = [item for item in items if item.id not in grouped_item_ids]
    department_groups.append(
        {
            "name": "Unassigned / Head Office",
            "items": other_items,
            "count": len(other_items),
        }
    )

    report_total = len(items)
    context = {
        "session": session,
        "items": items,
        "department_groups": department_groups,
        "report_status": "Completed" if session.is_closed else "In Progress",
        "report_total": report_total,
        "report_missing": sum(1 for item in items if item.status == "MISSING"),
        "report_repair": sum(1 for item in items if item.status == "IN_REPAIR"),
        "report_returned": sum(1 for item in items if item.status == "RETURNED_HEAD_OFFICE"),
    }
    return render(request, "HeadOffice/InventoryDetail.html", context)


@login_required
@permission_required("view_branch_devices")
def branch_devices(request):
    employee = _employee_for_user(request.user)
    branch = employee.branch if employee else None
    devices = Device.objects.select_related("assigned_employee", "assigned_branch").filter(assigned_branch=branch) if branch else Device.objects.none()
    return render(request, "BranchManage/BranchDevices.html", {"branch": branch, "devices": devices})


@login_required
@permission_required("view_branch_employees")
def branch_employees(request):
    employee = _employee_for_user(request.user)
    branch = employee.branch if employee else None
    employees = Employee.objects.select_related("department", "user").prefetch_related("device_set").filter(branch=branch) if branch else Employee.objects.none()
    return render(request, "BranchManage/BranchEmployees.html", {"branch": branch, "employees": employees})


@login_required
@permission_required("participate_inventory_verification")
def branch_inventory_verification(request):
    employee = _employee_for_user(request.user)
    branch = employee.branch if employee else None
    sessions = InventorySession.objects.select_related("branch", "created_by").prefetch_related(
        "items", "items__device", "items__device__assigned_employee"
    ).filter(branch=branch).order_by("-start_date") if branch else InventorySession.objects.none()
    return render(request, "BranchManage/InventoryVerification.html", {"branch": branch, "sessions": sessions})


@login_required
@permission_required("view_branch_reports")
def branch_reports(request):
    employee = _employee_for_user(request.user)
    branch = employee.branch if employee else None
    devices = Device.objects.filter(assigned_branch=branch) if branch else Device.objects.none()
    employees = Employee.objects.filter(branch=branch).prefetch_related("device_set") if branch else Employee.objects.none()
    sessions = InventorySession.objects.filter(branch=branch).prefetch_related("items") if branch else InventorySession.objects.none()
    context = {
        "branch": branch,
        "employees": employees,
        "missing_devices": devices.filter(status="MISSING"),
        "repair_devices": devices.filter(status="IN_REPAIR"),
        "sessions": sessions.order_by("-start_date"),
    }
    return render(request, "BranchManage/Reports.html", context)


def _apply_common_report_filters(request, employees, repairs, devices, audit_logs):
    branch_id = request.GET.get("branch")
    employee_id = request.GET.get("employee")
    selected_status = request.GET.get("status")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    if branch_id:
        employees = employees.filter(branch_id=branch_id)
        repairs = repairs.filter(Q(employee__branch_id=branch_id) | Q(device__assigned_branch_id=branch_id))
        devices = devices.filter(assigned_branch_id=branch_id)
    if employee_id:
        employees = employees.filter(id=employee_id)
        repairs = repairs.filter(employee_id=employee_id)
        devices = devices.filter(assigned_employee_id=employee_id)
    if selected_status:
        employees = employees.filter(status=selected_status) if selected_status in ["ACTIVE", "INACTIVE", "EXITED"] else employees
        repairs = repairs.filter(status=selected_status) if selected_status in dict(RepairRequest.STATUS_CHOICES) else repairs
        devices = devices.filter(status=selected_status) if selected_status in dict(Device.STATUS_CHOICES) else devices
        audit_logs = audit_logs.filter(action=selected_status) if selected_status.startswith("AUDIT:") else audit_logs
    if date_from:
        employees = employees.filter(hire_date__gte=date_from)
        repairs = repairs.filter(request_date__date__gte=date_from)
        audit_logs = audit_logs.filter(timestamp__date__gte=date_from)
    if date_to:
        employees = employees.filter(hire_date__lte=date_to)
        repairs = repairs.filter(request_date__date__lte=date_to)
        audit_logs = audit_logs.filter(timestamp__date__lte=date_to)

    return employees, repairs, devices, audit_logs


def _report_export_response(export_type, context):
    lines = [
        "Report,Metric,Value",
        f"Employees,Active,{context['active_employees']}",
        f"Employees,Inactive,{context['inactive_employees']}",
        f"Employees,Device Assignments,{context['device_assignments']}",
        f"Repairs,Pending,{context['pending_repairs']}",
        f"Repairs,Assigned,{context['assigned_repairs']}",
        f"Repairs,Completed,{context['completed_repairs']}",
        f"Inventory,Available,{context['available_inventory']}",
        f"Inventory,Assigned,{context['assigned_inventory']}",
        f"Inventory,Damaged,{context['damaged_inventory']}",
    ]
    content = "\n".join(lines)
    if export_type == "excel":
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="head-office-report.csv"'
        return response
    if export_type == "pdf":
        response = HttpResponse(content, content_type="text/plain")
        response["Content-Disposition"] = 'attachment; filename="head-office-report.pdf"'
        return response
    return None


@login_required
@permission_required("view_reports")
def head_office_reports(request):
    """Head Office reports with filters, summaries, and exports."""
    employees = Employee.objects.select_related("branch", "department", "user").all()
    repairs = RepairRequest.objects.select_related(
        "device", "device__assigned_branch", "employee", "employee__branch", "repairlog", "repairlog__technician"
    ).all()
    devices = Device.objects.select_related("assigned_employee", "assigned_branch").all()
    audit_logs = AuditLog.objects.select_related("user").all()

    employees, repairs, devices, audit_logs = _apply_common_report_filters(
        request, employees, repairs, devices, audit_logs
    )

    technician_performance = (
        RepairLog.objects.select_related("technician")
        .filter(repair_request__in=repairs)
        .values("technician__username")
        .annotate(completed=Count("id"))
        .order_by("-completed")
    )
    branch_stats = (
        devices.values("assigned_branch__name")
        .annotate(total=Count("id"), repairs=Count("repairrequest", filter=Q(repairrequest__status__in=["APPROVED", "IN_PROGRESS", "COMPLETED"])))
        .order_by("assigned_branch__name")
    )
    context = {
        "branches": Branch.objects.all().order_by("name"),
        "employees_filter": Employee.objects.all().order_by("full_name"),
        "selected": request.GET,
        "employee_rows": employees.order_by("full_name")[:100],
        "repair_rows": repairs.order_by("-request_date")[:100],
        "inventory_rows": devices.order_by("company_tag")[:100],
        "audit_rows": audit_logs.order_by("-timestamp")[:100],
        "technician_performance": technician_performance,
        "branch_stats": branch_stats,
        "active_employees": employees.filter(status="ACTIVE").count(),
        "inactive_employees": employees.filter(status="INACTIVE").count(),
        "device_assignments": DeviceAssignment.objects.filter(employee__in=employees, returned_date__isnull=True).count(),
        "pending_repairs": repairs.filter(status="PENDING").count(),
        "assigned_repairs": repairs.filter(status__in=["APPROVED", "IN_PROGRESS"]).count(),
        "completed_repairs": repairs.filter(status="COMPLETED").count(),
        "available_inventory": devices.filter(status="AVAILABLE").count(),
        "assigned_inventory": devices.filter(status="ASSIGNED").count(),
        "damaged_inventory": devices.filter(Q(status="IN_REPAIR") | Q(condition_notes__icontains="damaged")).count(),
        "branch_activity": audit_logs.filter(model_name__in=["Branch", "InventorySession", "Device"])[:50],
        "status_choices": list(Employee.STATUS_CHOICES) + list(RepairRequest.STATUS_CHOICES) + list(Device.STATUS_CHOICES),
    }

    export_response = _report_export_response(request.GET.get("export"), context)
    if export_response:
        return export_response
    return render(request, "HeadOffice/Reports.html", context)


@login_required
@permission_required("view_audit_logs")
def head_office_audit_logs(request):
    """Audit logs view."""
    audit_logs = AuditLog.objects.select_related('user').all().order_by('-timestamp')
    
    # Filter by action if provided
    action = request.GET.get('action')
    if action:
        audit_logs = audit_logs.filter(action=action)
    
    # Get unique actions for filter dropdown
    actions = AuditLog.objects.values_list('action', flat=True).distinct()
    
    context = {
        'audit_logs': audit_logs[:500],  # Show last 500
        'actions': actions,
        'selected_action': action,
    }
    return render(request, "HeadOffice/AuditLogs.html", context)


@login_required
@permission_required("view_access_control")
def access_control_roles(request):
    roles = Role.objects.prefetch_related("permissions", "users").all()
    modules = Module.objects.prefetch_related("permissions").all()
    return render(request, "HeadOffice/AccessControlRoles.html", {"roles": roles, "modules": modules})


@login_required
@permission_required("manage_permissions")
def access_control_permissions(request):
    modules = Module.objects.prefetch_related("permissions").all()
    return render(request, "HeadOffice/AccessControlPermissions.html", {"modules": modules})


@login_required
@permission_required("assign_role")
def access_control_assignments(request):
    employees = Employee.objects.select_related("user", "branch", "department").filter(is_deleted=False)
    roles = Role.objects.all().order_by("is_system", "name")
    return render(request, "HeadOffice/AccessControlAssignments.html", {"employees": employees, "roles": roles})
