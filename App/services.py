"""
Service layer containing all business logic.

This layer handles:
- Device assignment logic
- Repair workflow
- Inventory management
- Employee exit automation
- Device status updates
"""

from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from .models import (
    Device,
    DeviceAssignment,
    Employee,
    RepairRequest,
    RepairLog,
    InventoryItem,
    InventorySession,
    AuditLog,
    Notification,
)


class DeviceAssignmentService:
    """
    Handles device assignment operations.

    Business Rules:
    - Can't assign already assigned device
    - Updates device status to ASSIGNED
    - Updates device location info
    """

    @staticmethod
    def assign_device(device_id, employee_id, assigned_by_user, condition=None):
        """
        Assign device to employee.

        Args:
            device_id: Device to assign
            employee_id: Employee to assign to
            assigned_by_user: User performing the assignment
            condition: Condition on issue

        Returns:
            DeviceAssignment instance

        Raises:
            ValueError: If device already assigned or validation fails
        """
        device = Device.objects.get(id=device_id)
        employee = Employee.objects.get(id=employee_id)

        # Validation
        if device.status == "ASSIGNED":
            raise ValueError("Device is already assigned to someone")

        if device.status == "IN_REPAIR":
            raise ValueError("Device is currently in repair")

        if device.status == "MISSING":
            raise ValueError("Cannot assign missing device")

        if device.status == "RETIRED":
            raise ValueError("Cannot assign retired device")

        if employee.status != "ACTIVE":
            raise ValueError("Device can only be assigned to an active employee")

        if device.assigned_branch and device.assigned_branch_id != employee.branch_id:
            raise ValueError(
                f"Device is assigned to {device.assigned_branch.name} branch and can only be assigned to employees from that branch"
            )

        # Ensure no active assignment
        active_assignment = DeviceAssignment.objects.filter(
            device=device, returned_date__isnull=True
        ).exists()

        if active_assignment:
            raise ValueError("Device has active assignment")

        # Create assignment
        with transaction.atomic():
            assignment = DeviceAssignment.objects.create(
                device=device,
                employee=employee,
                branch=employee.branch,
                assigned_by=assigned_by_user,
                condition_on_issue=condition or "",
            )

            # Update device status
            device.status = "ASSIGNED"
            device.assigned_employee = employee
            device.assigned_branch = employee.branch
            device.location_type = "EMPLOYEE"
            device.current_location = (
                f"{employee.branch.name} - {employee.full_name}"
            )
            device.save()

            # Create audit log
            AuditLog.objects.create(
                user=assigned_by_user,
                action="DEVICE_ASSIGNED",
                model_name="Device",
                object_id=device.id,
                details=f"Assigned to {employee.full_name}",
            )

            return assignment

    @staticmethod
    def return_device(
        assignment_id, returned_by_user, condition_on_return=None
    ):
        """
        Return assigned device.

        Args:
            assignment_id: Assignment to return
            returned_by_user: User performing the return
            condition_on_return: Condition on return

        Returns:
            Updated DeviceAssignment instance
        """
        assignment = DeviceAssignment.objects.get(id=assignment_id)
        device = assignment.device

        if assignment.returned_date:
            raise ValueError("Device already returned")

        with transaction.atomic():
            # Mark as returned
            assignment.returned_date = timezone.now()
            assignment.received_by = returned_by_user
            assignment.condition_on_return = condition_on_return or ""
            assignment.save()

            # Update device status
            device.status = "AVAILABLE"
            device.assigned_employee = None
            device.assigned_branch = None
            device.location_type = "HEAD_OFFICE"
            device.current_location = "Head Office"
            device.save()

            # Create audit log
            AuditLog.objects.create(
                user=returned_by_user,
                action="DEVICE_RETURNED",
                model_name="Device",
                object_id=device.id,
                details=f"Returned by {assignment.employee.full_name}",
            )

            return assignment


class RepairService:
    """
    Handles repair request workflow.

    Business Rules:
    - Only HEAD_OFFICE can approve repairs
    - Only TECHNICIAN can complete repairs
    - Device moves to IN_REPAIR on approval
    - Device returns to ASSIGNED on completion
    """

    @staticmethod
    def create_repair_request(device_id, employee_id, issue_description, priority="NORMAL"):
        """
        Create repair request by employee.

        Args:
            device_id: Device needing repair
            employee_id: Employee requesting repair
            issue_description: Description of issue
            priority: Priority level

        Returns:
            RepairRequest instance
        """
        device = Device.objects.get(id=device_id)
        employee = Employee.objects.get(id=employee_id)

        # Validation
        if device.status not in ["ASSIGNED", "IN_REPAIR"]:
            raise ValueError(
                "Only assigned or in-repair devices can request repair"
            )

        if device.assigned_employee != employee:
            raise ValueError(
                "Employee can only request repair for assigned devices"
            )

        with transaction.atomic():
            repair_request = RepairRequest.objects.create(
                device=device,
                employee=employee,
                issue_description=issue_description,
                priority=priority,
                status="PENDING",
            )

            # Create audit log
            AuditLog.objects.create(
                user=employee.user,
                action="REPAIR_REQUESTED",
                model_name="RepairRequest",
                object_id=repair_request.id,
                details=issue_description,
            )

            return repair_request

    @staticmethod
    def approve_repair(repair_request_id, approved_by_user):
        """
        Approve repair request by HEAD_OFFICE.

        Args:
            repair_request_id: Repair request to approve
            approved_by_user: HEAD_OFFICE user approving

        Returns:
            Updated RepairRequest instance
        """
        repair_request = RepairRequest.objects.get(id=repair_request_id)
        device = repair_request.device

        if repair_request.status != "PENDING":
            raise ValueError("Can only approve pending repair requests")

        with transaction.atomic():
            repair_request.status = "APPROVED"
            repair_request.approved_by = approved_by_user
            repair_request.save()

            # Update device status
            device.status = "IN_REPAIR"
            device.save()

            # Create audit log
            AuditLog.objects.create(
                user=approved_by_user,
                action="REPAIR_APPROVED",
                model_name="RepairRequest",
                object_id=repair_request.id,
                details=f"Approved by {approved_by_user.username}",
            )

            return repair_request

    @staticmethod
    def reject_repair(repair_request_id, approved_by_user):
        """
        Reject repair request by HEAD_OFFICE.

        Args:
            repair_request_id: Repair request to reject
            approved_by_user: HEAD_OFFICE user rejecting

        Returns:
            Updated RepairRequest instance
        """
        repair_request = RepairRequest.objects.get(id=repair_request_id)

        if repair_request.status != "PENDING":
            raise ValueError("Can only reject pending repair requests")

        with transaction.atomic():
            repair_request.status = "REJECTED"
            repair_request.approved_by = approved_by_user
            repair_request.save()

            # Create audit log
            AuditLog.objects.create(
                user=approved_by_user,
                action="REPAIR_REJECTED",
                model_name="RepairRequest",
                object_id=repair_request.id,
                details=f"Rejected by {approved_by_user.username}",
            )

            return repair_request

    @staticmethod
    def complete_repair(repair_request_id, technician_user, notes, parts_used=None):
        """
        Complete repair by technician.

        Args:
            repair_request_id: Repair request to complete
            technician_user: Technician completing repair
            notes: Repair notes
            parts_used: Parts used in repair

        Returns:
            Updated RepairLog instance
        """
        repair_request = RepairRequest.objects.get(id=repair_request_id)
        device = repair_request.device

        if repair_request.status != "APPROVED":
            raise ValueError(
                "Can only complete approved repair requests"
            )

        with transaction.atomic():
            # Get or create repair log
            repair_log, created = RepairLog.objects.get_or_create(
                repair_request=repair_request
            )

            # Update repair log
            repair_log.technician = technician_user
            repair_log.notes = notes
            repair_log.parts_used = parts_used or ""
            repair_log.completed_date = timezone.now()
            repair_log.save()

            # Update repair request status
            repair_request.status = "COMPLETED"
            repair_request.save()

            # Update device status back to ASSIGNED
            device.status = "ASSIGNED"
            device.save()

            # Create audit log
            AuditLog.objects.create(
                user=technician_user,
                action="REPAIR_COMPLETED",
                model_name="RepairLog",
                object_id=repair_log.id,
                details=f"Completed by {technician_user.username}",
            )

            return repair_log


class InventoryService:
    """
    Handles inventory management.

    Business Rules:
    - Inventory sessions are branch-specific
    - Auto-load devices for branch
    - Track VERIFIED and MISSING devices
    """

    @staticmethod
    def create_inventory_session(branch_id, created_by_user):
        """
        Create inventory session for branch.

        Args:
            branch_id: Branch for inventory
            created_by_user: HEAD_OFFICE user creating session

        Returns:
            InventorySession instance
        """
        from .models import Branch

        branch = Branch.objects.get(id=branch_id)

        with transaction.atomic():
            session = InventorySession.objects.create(
                branch=branch,
                start_date=timezone.now(),
                created_by=created_by_user,
            )

            # Auto-load all devices for branch
            branch_devices = Device.objects.filter(
                Q(assigned_branch=branch)
                | Q(location_type="HEAD_OFFICE")
            )

            for device in branch_devices:
                InventoryItem.objects.create(
                    session=session, device=device, status="VERIFIED"
                )

            # Create audit log
            AuditLog.objects.create(
                user=created_by_user,
                action="INVENTORY_SESSION_CREATED",
                model_name="InventorySession",
                object_id=session.id,
                details=f"Session created for {branch.name}",
            )

            return session

    @staticmethod
    def mark_item_verified(item_id, verified_by_user, comment=None):
        """Mark inventory item as verified."""
        item = InventoryItem.objects.get(id=item_id)

        with transaction.atomic():
            item.status = "VERIFIED"
            item.comment = comment or ""
            item.save()

            # Create audit log
            AuditLog.objects.create(
                user=verified_by_user,
                action="INVENTORY_VERIFIED",
                model_name="InventoryItem",
                object_id=item.id,
                details=f"Device {item.device.company_tag} verified",
            )

    @staticmethod
    def mark_item_missing(item_id, verified_by_user, comment=None):
        """Mark inventory item as missing."""
        item = InventoryItem.objects.get(id=item_id)
        device = item.device

        with transaction.atomic():
            item.status = "MISSING"
            item.comment = comment or ""
            item.save()

            # Update device status
            device.status = "MISSING"
            device.save()

            # Create audit log
            AuditLog.objects.create(
                user=verified_by_user,
                action="INVENTORY_MISSING",
                model_name="InventoryItem",
                object_id=item.id,
                details=f"Device {device.company_tag} marked missing",
            )


class EmployeeExitService:
    """
    Handles employee exit automation.

    Business Rules:
    - When employee status = EXITED
    - Find all active assignments
    - Mark devices as PENDING_RETURN
    """

    @staticmethod
    def handle_employee_exit(employee_id):
        """
        Handle employee exit process.

        Args:
            employee_id: Employee exiting

        Returns:
            List of affected devices
        """
        employee = Employee.objects.get(id=employee_id)

        if employee.status != "EXITED":
            raise ValueError("Employee status must be EXITED")

        # Find active assignments
        active_assignments = DeviceAssignment.objects.filter(
            employee=employee, returned_date__isnull=True
        )

        affected_devices = []

        with transaction.atomic():
            for assignment in active_assignments:
                device = assignment.device

                # Update device status
                device.status = "PENDING_RETURN"
                device.save()
                affected_devices.append(device)

                # Create audit log
                AuditLog.objects.create(
                    action="EMPLOYEE_EXIT_DEVICE_PENDING",
                    model_name="Device",
                    object_id=device.id,
                    details=f"Employee {employee.full_name} exited - device pending return",
                )

                # Create notification for branch manager
                if employee.branch and employee.branch.manager:
                    Notification.objects.create(
                        user=employee.branch.manager.user,
                        message=f"Device {device.company_tag} assigned to {employee.full_name} is pending return due to employee exit.",
                    )

            return affected_devices


class AuditService:
    """Handles audit logging operations."""

    @staticmethod
    def log_action(user, action, model_name, object_id, details=None):
        """
        Create audit log entry.

        Args:
            user: User performing action
            action: Action name
            model_name: Model name
            object_id: Object ID
            details: Additional details
        """
        AuditLog.objects.create(
            user=user,
            action=action,
            model_name=model_name,
            object_id=object_id,
            details=details or "",
        )
