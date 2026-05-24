from django.contrib import admin
from .models import *


# =========================
# USER ADMIN
# =========================
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'dynamic_role', 'is_active', 'is_staff')
    list_filter = ('role', 'dynamic_role', 'is_active', 'is_staff')
    search_fields = ('username', 'email')
    ordering = ('username',)


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('module_name', 'key')
    search_fields = ('module_name', 'key')


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('permission_name', 'codename', 'module')
    list_filter = ('module',)
    search_fields = ('permission_name', 'codename')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_system', 'created_at')
    list_filter = ('is_system',)
    search_fields = ('name', 'code')


# =========================
# BRANCH ADMIN
# =========================
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'manager')
    search_fields = ('name', 'location')
    list_filter = ('location',)


# =========================
# DEPARTMENT ADMIN
# =========================
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch')
    list_filter = ('branch',)
    search_fields = ('name',)


# =========================
# EMPLOYEE ADMIN
# =========================
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'position', 'branch', 'department', 'status', 'hire_date')
    list_filter = ('status', 'branch', 'department')
    search_fields = ('full_name', 'position')
    autocomplete_fields = ('user', 'branch', 'department')


# =========================
# DEVICE ADMIN
# =========================
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        'company_tag',
        'device_type',
        'brand',
        'model',
        'status',
        'assigned_employee',
        'assigned_branch',
        'warranty_expiry'
    )

    list_filter = ('status', 'device_type', 'brand', 'assigned_branch')
    search_fields = ('company_tag', 'serial_number', 'brand', 'model')
    autocomplete_fields = ('assigned_employee', 'assigned_branch')

    readonly_fields = ('current_location',)

    fieldsets = (
        ("Device Info", {
            'fields': ('device_type', 'brand', 'model', 'serial_number', 'company_tag')
        }),
        ("Assignment", {
            'fields': ('assigned_employee', 'assigned_branch')
        }),
        ("Status & Location", {
            'fields': ('status', 'location_type', 'current_location')
        }),
        ("Dates", {
            'fields': ('purchase_date', 'warranty_expiry')
        }),
        ("Notes", {
            'fields': ('condition_notes',)
        }),
    )


# =========================
# DEVICE ASSIGNMENT ADMIN
# =========================
@admin.register(DeviceAssignment)
class DeviceAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'device',
        'employee',
        'branch',
        'assigned_by',
        'assigned_date',
        'returned_date'
    )

    list_filter = ('branch', 'assigned_date', 'returned_date')
    search_fields = ('device__company_tag', 'employee__full_name')
    autocomplete_fields = ('device', 'employee', 'branch', 'assigned_by', 'received_by')

    readonly_fields = ('assigned_date',)


# =========================
# REPAIR REQUEST ADMIN
# =========================
@admin.register(RepairRequest)
class RepairRequestAdmin(admin.ModelAdmin):
    list_display = (
        'device',
        'employee',
        'priority',
        'status',
        'request_date',
        'approved_by'
    )

    list_filter = ('status', 'priority')
    search_fields = ('device__company_tag', 'employee__full_name')
    autocomplete_fields = ('device', 'employee', 'approved_by')


# =========================
# REPAIR LOG ADMIN
# =========================
@admin.register(RepairLog)
class RepairLogAdmin(admin.ModelAdmin):
    list_display = (
        'repair_request',
        'technician',
        'start_date',
        'completed_date'
    )

    list_filter = ('start_date', 'completed_date')
    search_fields = ('repair_request__device__company_tag',)
    autocomplete_fields = ('repair_request', 'technician')


# =========================
# INVENTORY SESSION ADMIN
# =========================
@admin.register(InventorySession)
class InventorySessionAdmin(admin.ModelAdmin):
    list_display = (
        'branch',
        'start_date',
        'end_date',
        'approved_by_branch',
        'approved_by_head_office'
    )

    list_filter = ('branch', 'approved_by_branch', 'approved_by_head_office')

    autocomplete_fields = ('branch', 'created_by')

    search_fields = ('branch__name',)


# =========================
# INVENTORY ITEM ADMIN
# =========================
@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = (
        'session',
        'device',
        'status'
    )

    list_filter = ('status',)
    search_fields = ('device__company_tag',)
    autocomplete_fields = ('session', 'device')


# =========================
# NOTIFICATION ADMIN
# =========================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('user__username', 'message')


# =========================
# AUDIT LOG ADMIN
# =========================
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'model_name', 'timestamp')
    list_filter = ('model_name', 'timestamp')
    search_fields = ('action', 'user__username')

    readonly_fields = ('timestamp',)
