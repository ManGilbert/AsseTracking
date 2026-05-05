from django.urls import path
from .views import (
    home_view,
    login_view,
    logout_view,
    dashboard_redirect,
    head_office_dashboard,
    branch_manager_dashboard,
    employee_dashboard,
    technician_dashboard,
)

urlpatterns = [
    path("", home_view, name="home"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/", dashboard_redirect, name="dashboard_redirect"),
    path("dashboard/head-office/", head_office_dashboard, name="head_office_dashboard"),
    path("dashboard/branch/", branch_manager_dashboard, name="branch_manager_dashboard"),
    path("dashboard/employee/", employee_dashboard, name="employee_dashboard"),
    path("dashboard/technician/", technician_dashboard, name="technician_dashboard"),
]
