"""
Custom permission classes for role-based access control.

Permissions define which roles can perform which actions.
"""

from rest_framework import permissions
from .access_control import user_has_permission


class IsHeadOffice(permissions.BasePermission):
    """Allow access only to HEAD_OFFICE users."""

    message = "Only Head Office staff can access this resource."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "HEAD_OFFICE"
        )


class IsTechnician(permissions.BasePermission):
    """Allow access only to TECHNICIAN users."""

    message = "Only Technicians can access this resource."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "TECHNICIAN"
        )


class IsBranchManager(permissions.BasePermission):
    """Allow access only to BRANCH_MANAGER users."""

    message = "Only Branch Managers can access this resource."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "BRANCH_MANAGER"
        )


class IsEmployee(permissions.BasePermission):
    """Allow access only to EMPLOYEE users."""

    message = "Only Employees can access this resource."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "EMPLOYEE"
        )


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Allow access to own resources or read-only access.
    Used for employee-specific data.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check if the user is the employee or the owner
        if hasattr(obj, "employee"):
            return obj.employee.user == request.user
        if hasattr(obj, "user"):
            return obj.user == request.user

        return False


class IsAuthenticated(permissions.BasePermission):
    """Allow access only to authenticated users."""

    message = "Authentication is required."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class CanManageDevices(permissions.BasePermission):
    """Allow HEAD_OFFICE to manage devices."""

    message = "Only Head Office staff can manage devices."

    def has_permission(self, request, view):
        action_permissions = {
            "create": "add_device",
            "update": "update_device",
            "partial_update": "update_device",
            "destroy": "delete_device",
            "decommission": "decommission_device",
            "restore": "restore_device",
            "permanent_delete": "delete_device",
        }
        return user_has_permission(request.user, action_permissions.get(getattr(view, "action", ""), "update_device"))


class CanManageAssignments(permissions.BasePermission):
    """Allow HEAD_OFFICE to manage device assignments."""

    message = "Only Head Office staff can manage device assignments."

    def has_permission(self, request, view):
        action_permissions = {
            "create": "assign_device",
            "update": "update_assignment",
            "partial_update": "update_assignment",
            "destroy": "delete_assignment",
            "return_device": "return_device",
        }
        return user_has_permission(request.user, action_permissions.get(getattr(view, "action", ""), "assign_device"))


class CanRequestRepair(permissions.BasePermission):
    """Allow EMPLOYEE to request repairs."""

    message = "Only Employees can request repairs."

    def has_permission(self, request, view):
        return user_has_permission(request.user, "request_repair") or user_has_permission(request.user, "submit_repair_request")


class CanApproveRepair(permissions.BasePermission):
    """Allow HEAD_OFFICE to approve/reject repairs."""

    message = "Only Head Office staff can approve repairs."

    def has_permission(self, request, view):
        return user_has_permission(request.user, "approve_repairs")


class CanUpdateRepair(permissions.BasePermission):
    """Allow TECHNICIAN to update repair logs."""

    message = "Only Technicians can update repair logs."

    def has_permission(self, request, view):
        action_permissions = {
            "start": "start_repair",
            "update": "update_repair",
            "partial_update": "update_repair",
            "update_repair": "update_repair",
            "complete": "complete_repair",
        }
        return user_has_permission(request.user, action_permissions.get(getattr(view, "action", ""), "update_repair"))


class CanVerifyInventory(permissions.BasePermission):
    """Allow Branch Managers and Head Office to verify inventory."""

    message = "Only Branch Managers or Head Office can verify inventory."

    def has_permission(self, request, view):
        return user_has_permission(request.user, "verify_inventory") or user_has_permission(request.user, "participate_inventory_verification")


class CanCreateInventorySession(permissions.BasePermission):
    """Allow HEAD_OFFICE to create inventory sessions."""

    message = "Only Head Office staff can create inventory sessions."

    def has_permission(self, request, view):
        action_permissions = {
            "create": "create_inventory_session",
            "update": "create_inventory_session",
            "partial_update": "create_inventory_session",
            "destroy": "create_inventory_session",
            "close": "close_inventory",
            "approve_head_office": "approve_inventory",
            "register_found_device": "verify_inventory",
        }
        return user_has_permission(request.user, action_permissions.get(getattr(view, "action", ""), "create_inventory_session"))


class HasAppPermission(permissions.BasePermission):
    message = "You do not have permission to perform this action."

    def __init__(self, codename):
        self.codename = codename

    def has_permission(self, request, view):
        return user_has_permission(request.user, self.codename)


class HasAnyAppPermission(permissions.BasePermission):
    message = "You do not have permission to access this resource."

    def __init__(self, *codenames):
        self.codenames = codenames

    def has_permission(self, request, view):
        return any(user_has_permission(request.user, codename) for codename in self.codenames)
