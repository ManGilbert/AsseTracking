"""
URL configuration for App API.

Routes all ViewSets to their API endpoints with proper naming.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

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

urlpatterns = [
    path("", include(router.urls)),
    path("auth/", include(jwt_urls)),
]
