from django.urls import path
from .views import (
    home_view,
    login_view,
    logout_view,
    dashboard_redirect,
    head_office_dashboard,
    head_office_employees,
    head_office_branches,
    head_office_devices,
    head_office_assignments,
    head_office_repairs,
    head_office_inventory,
    head_office_audit_logs,
    branch_manager_dashboard,
    employee_dashboard,
    technician_dashboard,
)

urlpatterns = [
    path("", home_view, name="home"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/", dashboard_redirect, name="dashboard_redirect"),
    
    # Head Office Routes
    path("dashboard/head-office/", head_office_dashboard, name="head_office_dashboard"),
    path("head-office/employees/", head_office_employees, name="head_office_employees"),
    path("head-office/branches/", head_office_branches, name="head_office_branches"),
    path("head-office/devices/", head_office_devices, name="head_office_devices"),
    path("head-office/assignments/", head_office_assignments, name="head_office_assignments"),
    path("head-office/repairs/", head_office_repairs, name="head_office_repairs"),
    path("head-office/inventory/", head_office_inventory, name="head_office_inventory"),
    path("head-office/audit-logs/", head_office_audit_logs, name="head_office_audit_logs"),
    
    # Other Dashboards
    path("dashboard/branch/", branch_manager_dashboard, name="branch_manager_dashboard"),
    path("dashboard/employee/", employee_dashboard, name="employee_dashboard"),
    path("dashboard/technician/", technician_dashboard, name="technician_dashboard"),
]
