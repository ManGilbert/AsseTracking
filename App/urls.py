"""
URL configuration for App API.

Routes all ViewSets to their API endpoints with proper naming.
"""

from django.urls import path, include
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.reverse import reverse
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .openapi import api_index

from .views import (
    UserViewSet,
    RoleViewSet,
    ModuleViewSet,
    PermissionViewSet,
    AccessControlViewSet,
    BranchViewSet,
    DepartmentViewSet,
    EmployeeViewSet,
    DeviceViewSet,
    DeviceAssignmentViewSet,
    RepairRequestViewSet,
    RepairLogViewSet,
    InventorySessionViewSet,
    InventoryItemViewSet,
    NotificationViewSet,
    AuditLogViewSet,
)

# Initialize router
router = DefaultRouter()

# Register ViewSets
router.register(r"users", UserViewSet, basename="user")
router.register(r"roles", RoleViewSet, basename="role")
router.register(r"modules", ModuleViewSet, basename="module")
router.register(r"permissions", PermissionViewSet, basename="permission")
router.register(r"access-control", AccessControlViewSet, basename="access-control")
router.register(r"branches", BranchViewSet, basename="branch")
router.register(r"departments", DepartmentViewSet, basename="department")
router.register(r"employees", EmployeeViewSet, basename="employee")
router.register(r"devices", DeviceViewSet, basename="device")
router.register(r"assignments", DeviceAssignmentViewSet, basename="assignment")
router.register(r"repair-requests", RepairRequestViewSet, basename="repair-request")
router.register(r"repair-logs", RepairLogViewSet, basename="repair-log")
router.register(r"inventory-sessions", InventorySessionViewSet, basename="inventory-session")
router.register(r"inventory-items", InventoryItemViewSet, basename="inventory-item")
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")

# JWT Authentication endpoints
jwt_urls = [
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request, format=None):
    return Response({
        "users": reverse("user-list", request=request, format=format),
        "roles": reverse("role-list", request=request, format=format),
        "modules": reverse("module-list", request=request, format=format),
        "permissions": reverse("permission-list", request=request, format=format),
        "access_control": reverse("access-control-list", request=request, format=format),
        "branches": reverse("branch-list", request=request, format=format),
        "departments": reverse("department-list", request=request, format=format),
        "employees": reverse("employee-list", request=request, format=format),
        "devices": reverse("device-list", request=request, format=format),
        "assignments": reverse("assignment-list", request=request, format=format),
        "repair_requests": reverse("repair-request-list", request=request, format=format),
        "repair_logs": reverse("repair-log-list", request=request, format=format),
        "inventory_sessions": reverse("inventory-session-list", request=request, format=format),
        "inventory_items": reverse("inventory-item-list", request=request, format=format),
        "notifications": reverse("notification-list", request=request, format=format),
        "audit_logs": reverse("audit-log-list", request=request, format=format),
        "auth_token": reverse("token_obtain_pair", request=request, format=format),
        "auth_token_refresh": reverse("token_refresh", request=request, format=format),
        "schema": reverse("schema", request=request, format=format),
        "docs": reverse("swagger-ui", request=request, format=format),
        "redoc": reverse("redoc", request=request, format=format),
    })

urlpatterns = [
    # Use schema-based index (open) so the root lists all endpoints reliably
    path("", api_index, name="api-root"),
    path("", include(router.urls)),
    path("auth/", include(jwt_urls)),
]
