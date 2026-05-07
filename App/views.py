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
from django.db.models import Count, Q
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

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

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


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

    def perform_create(self, serializer):
        branch = serializer.save()
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
        branch_id = instance.id
        branch_name = instance.name
        instance.delete()
        AuditService.log_action(
            self.request.user,
            "BRANCH_DELETED",
            "Branch",
            branch_id,
            f"Branch: {branch_name}",
        )


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

    def perform_create(self, serializer):
        department = serializer.save()
        AuditService.log_action(
            self.request.user,
            "DEPARTMENT_CREATED",
            "Department",
            department.id,
            f"Department: {department.name}",
        )

    def perform_destroy(self, instance):
        department_id = instance.id
        department_name = instance.name
        instance.delete()
        AuditService.log_action(
            self.request.user,
            "DEPARTMENT_DELETED",
            "Department",
            department_id,
            f"Department: {department_name}",
        )


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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == "create":
            context["include_default_password"] = True
        return context

    def perform_create(self, serializer):
        employee = serializer.save()
        AuditService.log_action(
            self.request.user,
            "EMPLOYEE_CREATED",
            "Employee",
            employee.id,
            f"Employee: {employee.full_name}; username: {employee.user.username if employee.user else 'none'}",
        )

    def perform_update(self, serializer):
        employee = serializer.save()
        AuditService.log_action(
            self.request.user,
            "EMPLOYEE_UPDATED",
            "Employee",
            employee.id,
            f"Employee: {employee.full_name}",
        )

    def perform_destroy(self, instance):
        employee_id = instance.id
        employee_name = instance.full_name
        user = instance.user
        instance.delete()
        if user:
            user.delete()
        AuditService.log_action(
            self.request.user,
            "EMPLOYEE_DELETED",
            "Employee",
            employee_id,
            f"Employee: {employee_name}",
        )

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

    def get_queryset(self):
        queryset = Device.objects.select_related("assigned_employee", "assigned_branch")
        user = self.request.user
        if user.is_authenticated and user.role == "EMPLOYEE":
            return queryset.filter(assigned_employee__user=user)
        return queryset

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
        instance.delete()
        AuditService.log_action(
            self.request.user,
            "DEVICE_DELETED",
            "Device",
            device_id,
            f"Device: {device_tag}",
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.has_activity_history():
            return Response(
                {
                    "error": (
                        "Device cannot be deleted because it has related "
                        "activity/history."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            return super().destroy(request, *args, **kwargs)
        except DjangoValidationError as exc:
            return Response({"error": "; ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)


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
        if user.is_authenticated and user.role == "EMPLOYEE":
            return queryset.filter(employee__user=user)
        if user.is_authenticated and user.role == "TECHNICIAN":
            return queryset.filter(status__in=["APPROVED", "IN_PROGRESS", "COMPLETED"])
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return RepairRequestListSerializer
        return RepairRequestSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated()]
        elif self.action in ["approve", "reject", "reassign_completed"]:
            return [IsHeadOffice()]
        elif self.action in ["update", "partial_update", "destroy"]:
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

    @action(detail=True, methods=["post"], permission_classes=[CanUpdateRepair])
    def start_repair(self, request, pk=None):
        """Start an approved repair request."""
        repair_request = self.get_object()
        notes = request.data.get("notes", "")
        parts_used = request.data.get("parts_used", "")

        try:
            repair_log = RepairService.start_repair(
                repair_request.id,
                request.user,
                notes,
                parts_used,
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
            assignment = DeviceAssignmentService.assign_device(
                device_id=repair_request.device_id,
                employee_id=repair_request.employee_id,
                assigned_by_user=request.user,
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
        if user.is_authenticated and user.role == "TECHNICIAN":
            return queryset.filter(Q(technician=user) | Q(repair_request__status="COMPLETED"))
        if user.is_authenticated and user.role == "EMPLOYEE":
            return queryset.filter(repair_request__employee__user=user)
        return queryset

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
            "approve_head_office",
            "approve_branch",
            "close",
        ]:
            if self.action == "approve_branch":
                return [CanVerifyInventory()]
            return [CanCreateInventorySession()]
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
        session_id = instance.id
        branch_name = instance.branch.name
        instance.delete()
        AuditService.log_action(
            self.request.user,
            "INVENTORY_SESSION_DELETED",
            "InventorySession",
            session_id,
            f"Session for {branch_name}",
        )

    @action(detail=True, methods=["post"], permission_classes=[CanCreateInventorySession])
    def approve_head_office(self, request, pk=None):
        session = self.get_object()
        session.approved_by_head_office = True
        if not session.end_date:
            from django.utils import timezone
            session.end_date = timezone.now()
        session.save()
        AuditService.log_action(
            request.user,
            "INVENTORY_APPROVED_HEAD_OFFICE",
            "InventorySession",
            session.id,
            f"Session for {session.branch.name}",
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
            "mark_missing",
            "mark_extra",
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

        inactive_user = User.objects.filter(
            Q(username=username_or_email) | Q(email=username_or_email),
            is_active=False,
        ).first()
        if inactive_user:
            messages.error(request, "Your account is inactive. Please contact the administrator.")
            return render(request, "Auth/login.html", {"username": username_or_email})

        messages.error(request, "Invalid username/email or password")
        return render(request, "Auth/login.html", {"username": username_or_email})

    if request.GET.get("message"):
        messages.error(request, request.GET["message"])
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
    employee = _employee_for_user(request.user)
    branch = employee.branch if employee else None
    devices = Device.objects.filter(assigned_branch=branch) if branch else Device.objects.none()
    employees = Employee.objects.filter(branch=branch) if branch else Employee.objects.none()
    context = {
        "branch": branch,
        "device_count": devices.count(),
        "employee_count": employees.count(),
        "missing_count": devices.filter(status="MISSING").count(),
        "repair_count": devices.filter(status="IN_REPAIR").count(),
        "sessions": InventorySession.objects.filter(branch=branch).order_by("-start_date")[:5] if branch else [],
    }
    return render(request, "BranchManage/Dashboard.html", context)


@login_required
@role_required("EMPLOYEE")
def employee_dashboard(request):
    employee = Employee.objects.filter(user=request.user).first()
    devices = Device.objects.filter(assigned_employee=employee) if employee else Device.objects.none()
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
@role_required("TECHNICIAN")
def technician_dashboard(request):
    repairs = RepairRequest.objects.select_related("device", "employee").filter(
        status__in=["APPROVED", "IN_PROGRESS", "COMPLETED"]
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
@role_required("TECHNICIAN")
def technician_repairs(request):
    repairs = RepairRequest.objects.select_related(
        "device", "device__assigned_branch", "device__assigned_employee", "employee"
    ).filter(status="APPROVED").order_by("-request_date")
    return render(request, "Technician/Repairs.html", {"repairs": repairs})


@login_required
@role_required("TECHNICIAN")
def technician_in_progress_repairs(request):
    repairs = RepairRequest.objects.select_related(
        "device", "device__assigned_branch", "employee"
    ).filter(status="IN_PROGRESS").order_by("-request_date")
    return render(request, "Technician/InProgressRepairs.html", {"repairs": repairs})


@login_required
@role_required("TECHNICIAN")
def technician_completed_repairs(request):
    repair_logs = RepairLog.objects.select_related(
        "repair_request", "repair_request__device", "repair_request__employee", "technician"
    ).filter(repair_request__status="COMPLETED").order_by("-completed_date", "-start_date")
    return render(request, "Technician/CompletedRepairs.html", {"repair_logs": repair_logs})


@login_required
@role_required("TECHNICIAN")
def technician_device_lookup(request):
    devices = Device.objects.select_related("assigned_employee", "assigned_branch").all().order_by("company_tag")
    return render(request, "Technician/DeviceLookup.html", {"devices": devices})


@login_required
@role_required("TECHNICIAN")
def technician_repair_history(request):
    repair_logs = RepairLog.objects.select_related(
        "repair_request", "repair_request__device", "repair_request__employee", "technician"
    ).all().order_by("-start_date")
    return render(request, "Technician/RepairHistory.html", {"repair_logs": repair_logs})


@login_required
@role_required("HEAD_OFFICE", "BRANCH_MANAGER", "TECHNICIAN", "EMPLOYEE")
def employee_my_devices(request):
    employee = _employee_for_user(request.user)
    devices = Device.objects.select_related("assigned_branch").filter(assigned_employee=employee) if employee else Device.objects.none()
    return render(request, "Employee/MyDevices.html", {"employee": employee, "devices": devices})


@login_required
@role_required("HEAD_OFFICE", "BRANCH_MANAGER", "TECHNICIAN", "EMPLOYEE")
def employee_request_repair(request):
    employee = _employee_for_user(request.user)
    devices = Device.objects.filter(assigned_employee=employee).exclude(status__in=["RETIRED", "MISSING"]) if employee else Device.objects.none()
    return render(request, "Employee/RequestRepair.html", {"employee": employee, "devices": devices})


@login_required
@role_required("HEAD_OFFICE", "BRANCH_MANAGER", "TECHNICIAN", "EMPLOYEE")
def employee_repair_requests(request):
    employee = _employee_for_user(request.user)
    repairs = RepairRequest.objects.select_related("device", "approved_by", "employee").filter(employee=employee).order_by("-request_date") if employee else RepairRequest.objects.none()
    repairs = _attach_repair_activity(repairs) if employee else repairs
    return render(request, "Employee/RepairRequests.html", {"employee": employee, "repairs": repairs})


# =========================
# HEAD OFFICE MANAGEMENT VIEWS
# =========================

@login_required
@role_required("HEAD_OFFICE")
def head_office_employees(request):
    """Employee management view."""
    employees = Employee.objects.select_related(
        'user', 'branch', 'department'
    ).prefetch_related('device_set').all()
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
    branches = Branch.objects.prefetch_related(
        'departments',
        'employees',
        'employees__device_set',
        'employees__department',
    ).all()
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
    employees = Employee.objects.select_related('branch').filter(status='ACTIVE')
    statuses = Device._meta.get_field('status').choices
    location_types = Device._meta.get_field('location_type').choices
    device_types = Device.objects.values_list('device_type', flat=True).distinct()
    device_type_counts = (
        Device.objects.values('device_type')
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
    available_devices = Device.objects.select_related('assigned_branch').filter(status__in=['AVAILABLE', 'REPAIRED', 'COMPLETED'])
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
@role_required("HEAD_OFFICE")
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
        'devices': Device.objects.select_related('assigned_employee').exclude(assigned_employee__isnull=True),
        'employees': Employee.objects.filter(status='ACTIVE'),
    }
    return render(request, "HeadOffice/RequestRepairs.html", context)


@login_required
@role_required("HEAD_OFFICE")
def head_office_inventory(request):
    """Inventory management view."""
    inventory_sessions = InventorySession.objects.select_related(
        'branch', 'created_by'
    ).prefetch_related('items', 'items__device', 'items__device__assigned_employee').all().order_by('-start_date')
    
    branches = Branch.objects.all()
    
    context = {
        'inventory_sessions': inventory_sessions,
        'branches': branches,
    }
    return render(request, "HeadOffice/Inventory.html", context)


@login_required
@role_required("BRANCH_MANAGER")
def branch_devices(request):
    employee = _employee_for_user(request.user)
    branch = employee.branch if employee else None
    devices = Device.objects.select_related("assigned_employee", "assigned_branch").filter(assigned_branch=branch) if branch else Device.objects.none()
    return render(request, "BranchManage/BranchDevices.html", {"branch": branch, "devices": devices})


@login_required
@role_required("BRANCH_MANAGER")
def branch_employees(request):
    employee = _employee_for_user(request.user)
    branch = employee.branch if employee else None
    employees = Employee.objects.select_related("department", "user").prefetch_related("device_set").filter(branch=branch) if branch else Employee.objects.none()
    return render(request, "BranchManage/BranchEmployees.html", {"branch": branch, "employees": employees})


@login_required
@role_required("BRANCH_MANAGER")
def branch_inventory_verification(request):
    employee = _employee_for_user(request.user)
    branch = employee.branch if employee else None
    sessions = InventorySession.objects.select_related("branch", "created_by").prefetch_related(
        "items", "items__device", "items__device__assigned_employee"
    ).filter(branch=branch).order_by("-start_date") if branch else InventorySession.objects.none()
    return render(request, "BranchManage/InventoryVerification.html", {"branch": branch, "sessions": sessions})


@login_required
@role_required("BRANCH_MANAGER")
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
