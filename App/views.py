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
