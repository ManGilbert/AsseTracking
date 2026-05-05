"""
Custom permission classes for role-based access control.

Permissions define which roles can perform which actions.
"""

from rest_framework import permissions


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
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "HEAD_OFFICE"
        )


class CanManageAssignments(permissions.BasePermission):
    """Allow HEAD_OFFICE to manage device assignments."""

    message = "Only Head Office staff can manage device assignments."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "HEAD_OFFICE"
        )


class CanRequestRepair(permissions.BasePermission):
    """Allow EMPLOYEE to request repairs."""

    message = "Only Employees can request repairs."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "EMPLOYEE"
        )


class CanApproveRepair(permissions.BasePermission):
    """Allow HEAD_OFFICE to approve/reject repairs."""

    message = "Only Head Office staff can approve repairs."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "HEAD_OFFICE"
        )


class CanUpdateRepair(permissions.BasePermission):
    """Allow TECHNICIAN to update repair logs."""

    message = "Only Technicians can update repair logs."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "TECHNICIAN"
        )


class CanVerifyInventory(permissions.BasePermission):
    """Allow BRANCH_MANAGER to verify inventory."""

    message = "Only Branch Managers can verify inventory."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "BRANCH_MANAGER"
        )


class CanCreateInventorySession(permissions.BasePermission):
    """Allow HEAD_OFFICE to create inventory sessions."""

    message = "Only Head Office staff can create inventory sessions."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "HEAD_OFFICE"
        )
