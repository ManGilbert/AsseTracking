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
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse

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

from .serializers import (
    UserSerializer,
    UserCreateSerializer,
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
)
from .decorators import role_required

from .services import (
    DeviceAssignmentService,
    RepairService,
    InventoryService,
    EmployeeExitService,
    AuditService,
)


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
            return [IsHeadOffice()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Set user as inactive by default."""
        serializer.save(is_active=True)


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

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsHeadOffice()]
        return [IsAuthenticated()]


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

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsHeadOffice()]
        return [IsAuthenticated()]


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
        ]:
            return [IsHeadOffice()]
        return [IsAuthenticated()]

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

    def get_serializer_class(self):
        if self.action == "list":
            return DeviceListSerializer
        return DeviceSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [CanManageDevices()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Set created device as available."""
        device = serializer.save(status="AVAILABLE")
        AuditService.log_action(
            self.request.user,
            "DEVICE_CREATED",
            "Device",
            device.id,
            f"Device: {device.company_tag}",
        )


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

    def get_serializer_class(self):
        if self.action == "list":
            return RepairRequestListSerializer
        return RepairRequestSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsEmployee()]
        elif self.action in ["approve", "reject"]:
            return [IsHeadOffice()]
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

        # Get employee for current user
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

    @action(
        detail=True, methods=["post"], permission_classes=[IsHeadOffice]
    )
    def approve(self, request, pk=None):
        """
        Approve repair request.

        POST /api/repair-requests/{id}/approve/
        """
        repair_request = self.get_object()

        try:
            approved_request = RepairService.approve_repair(
                repair_request.id, request.user
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

    def get_permissions(self):
        if self.action in ["update_repair", "partial_update", "update"]:
            return [CanUpdateRepair()]
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

    def get_permissions(self):
        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
        ]:
            return [CanCreateInventorySession()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        """Create inventory session."""
        branch_id = request.data.get("branch_id")

        if not branch_id:
            return Response(
                {"error": "branch_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = InventoryService.create_inventory_session(
                branch_id, request.user
            )

            serializer = InventorySessionSerializer(session)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


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
            "mark_missing",
            "update",
            "partial_update",
        ]:
            return [CanVerifyInventory()]
        return [IsAuthenticated()]

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
    permission_classes = [IsHeadOffice]
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


def home_view(request):
    """Root view: redirect to login if not authenticated, dashboard if authenticated."""
    if request.user.is_authenticated:
        return redirect(_get_dashboard_url(request.user.role))
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
            return redirect(_get_dashboard_url(user.role))

        messages.error(request, "Invalid username/email or password")
        return render(request, "Auth/login.html", {"username": username_or_email})

    return render(request, "Auth/login.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard_redirect(request):
    return redirect(_get_dashboard_url(request.user.role))


@login_required
@role_required("HEAD_OFFICE")
def head_office_dashboard(request):
    """Head Office Dashboard with complete system overview."""
    from django.db.models import Count, Q
    
    # Device Statistics
    total_devices = Device.objects.count()
    assigned_devices = Device.objects.filter(status='ASSIGNED').count()
    available_devices = Device.objects.filter(status='AVAILABLE').count()
    in_repair_devices = Device.objects.filter(status='IN_REPAIR').count()
    missing_devices = Device.objects.filter(status='MISSING').count()
    
    # Calculate percentages
    percentage_assigned = round((assigned_devices / total_devices * 100) if total_devices > 0 else 0, 1)
    
    # Employee Statistics
    total_employees = Employee.objects.count()
    active_employees = Employee.objects.filter(status='ACTIVE').count()
    inactive_employees = Employee.objects.filter(status='INACTIVE').count()
    exited_employees = Employee.objects.filter(status='EXITED').count()
    
    # Branch Statistics
    total_branches = Branch.objects.count()
    
    # Repair Statistics
    pending_repairs = RepairRequest.objects.filter(status='PENDING').count()
    approved_repairs = RepairRequest.objects.filter(status='APPROVED').count()
    completed_repairs = RepairRequest.objects.filter(status='COMPLETED').count()
    
    # Recent Activities
    recent_audits = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]
    
    # Recent Repair Requests
    recent_repairs = RepairRequest.objects.select_related('device', 'employee', 'approved_by').order_by('-request_date')[:5]
    
    # Device Status Distribution for Charts
    device_status_data = Device.objects.values('status').annotate(count=Count('id'))
    
    # Device Type Distribution
    device_type_data = Device.objects.values('device_type').annotate(count=Count('id'))
    
    # Devices per Branch
    branch_device_data = Device.objects.values('assigned_branch__name').annotate(count=Count('id')).exclude(assigned_branch__isnull=True)
    
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
@role_required("BRANCH_MANAGER")
def branch_manager_dashboard(request):
    return render(request, "BranchManage/Dashboard.html")


@login_required
@role_required("EMPLOYEE")
def employee_dashboard(request):
    return render(request, "Employee/Dashboard.html")


@login_required
@role_required("TECHNICIAN")
def technician_dashboard(request):
    return render(request, "Technician/Dashboard.html")


# =========================
# HEAD OFFICE MANAGEMENT VIEWS
# =========================

@login_required
@role_required("HEAD_OFFICE")
def head_office_employees(request):
    """Employee management view."""
    employees = Employee.objects.select_related('user', 'branch', 'department').all()
    branches = Branch.objects.all()
    departments = Department.objects.all()
    users = User.objects.filter(role__in=['EMPLOYEE', 'BRANCH_MANAGER', 'TECHNICIAN'])
    
    context = {
        'employees': employees,
        'branches': branches,
        'departments': departments,
        'users': users,
        'statuses': Employee._meta.get_field('status').choices,
    }
    return render(request, "HeadOffice/Employee.html", context)


@login_required
@role_required("HEAD_OFFICE")
def head_office_branches(request):
    """Branch and department management view."""
    branches = Branch.objects.prefetch_related('departments', 'employees').all()
    context = {
        'branches': branches,
    }
    return render(request, "HeadOffice/Branches.html", context)


@login_required
@role_required("HEAD_OFFICE")
def head_office_devices(request):
    """Device management view."""
    devices = Device.objects.select_related('assigned_employee', 'assigned_branch').all()
    branches = Branch.objects.all()
    statuses = Device._meta.get_field('status').choices
    device_types = Device.objects.values_list('device_type', flat=True).distinct()
    
    context = {
        'devices': devices,
        'branches': branches,
        'statuses': statuses,
        'device_types': device_types,
    }
    return render(request, "HeadOffice/Devices.html", context)


@login_required
@role_required("HEAD_OFFICE")
def head_office_assignments(request):
    """Device assignment management view."""
    assignments = DeviceAssignment.objects.select_related(
        'device', 'employee', 'branch', 'assigned_by', 'received_by'
    ).all().order_by('-assigned_date')
    
    active_assignments = assignments.filter(returned_date__isnull=True)
    returned_assignments = assignments.filter(returned_date__isnull=False)
    
    employees = Employee.objects.filter(status='ACTIVE')
    branches = Branch.objects.all()
    
    context = {
        'assignments': assignments,
        'active_assignments': active_assignments,
        'returned_assignments': returned_assignments,
        'employees': employees,
        'branches': branches,
    }
    return render(request, "HeadOffice/Assignments.html", context)


@login_required
@role_required("HEAD_OFFICE")
def head_office_repairs(request):
    """Repair request management view."""
    repairs = RepairRequest.objects.select_related(
        'device', 'employee', 'approved_by'
    ).all().order_by('-request_date')
    
    repairs_by_status = {
        'PENDING': repairs.filter(status='PENDING'),
        'APPROVED': repairs.filter(status='APPROVED'),
        'REJECTED': repairs.filter(status='REJECTED'),
        'IN_PROGRESS': repairs.filter(status='IN_PROGRESS'),
        'COMPLETED': repairs.filter(status='COMPLETED'),
    }
    
    context = {
        'repairs': repairs,
        'repairs_by_status': repairs_by_status,
        'statuses': RepairRequest._meta.get_field('status').choices,
    }
    return render(request, "HeadOffice/RequestRepairs.html", context)


@login_required
@role_required("HEAD_OFFICE")
def head_office_inventory(request):
    """Inventory management view."""
    inventory_sessions = InventorySession.objects.select_related(
        'branch', 'created_by'
    ).all().order_by('-start_date')
    
    branches = Branch.objects.all()
    
    context = {
        'inventory_sessions': inventory_sessions,
        'branches': branches,
    }
    return render(request, "HeadOffice/Inventory.html", context)


@login_required
@role_required("HEAD_OFFICE")
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
