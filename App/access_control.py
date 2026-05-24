SYSTEM_ROLE_LABELS = {
    "HEAD_OFFICE": "Head Office",
    "BRANCH_MANAGER": "Branch Manager",
    "TECHNICIAN": "Technician",
    "EMPLOYEE": "Employee",
}

MODULE_DEFINITIONS = [
    ("head_office_dashboard", "Head Office Dashboard", "Main dashboard access"),
    ("employee_management", "Employee Management", "Manage employees"),
    ("branch_management", "Branch Management", "Manage branches"),
    ("department_management", "Department Management", "Manage departments"),
    ("device_management", "Device Management", "Manage devices"),
    ("device_assignments", "Device Assignments", "Assign and return devices"),
    ("repair_management", "Repair Management", "Handle repairs"),
    ("inventory_management", "Inventory Management", "Inventory verification"),
    ("audit_devices", "Audit Devices", "Device audit operations"),
    ("system_audit_logs", "System Audit Logs", "View system logs"),
    ("head_office_reports", "Head Office Reports", "View reports and analytics"),
    ("access_control", "Access Control", "Manage users, roles, and permissions"),
    ("employee_self_service", "Employee Self Service", "Employee device and repair self service"),
    ("branch_operations", "Branch Operations", "Branch manager operations"),
    ("technician_tasks", "Technician Tasks", "Technician repair workbench"),
]

PERMISSION_DEFINITIONS = {
    "head_office_dashboard": [
        ("view_head_office_dashboard", "View Head Office Dashboard"),
    ],
    "employee_management": [
        ("view_employee", "View Employee"),
        ("add_employee", "Add Employee"),
        ("update_employee", "Update Employee"),
        ("delete_employee", "Delete Employee"),
        ("reset_employee_password", "Reset Employee Password"),
    ],
    "branch_management": [
        ("view_branch", "View Branch"),
        ("add_branch", "Add Branch"),
        ("update_branch", "Update Branch"),
        ("delete_branch", "Delete Branch"),
    ],
    "department_management": [
        ("view_department", "View Department"),
        ("add_department", "Add Department"),
        ("update_department", "Update Department"),
        ("delete_department", "Delete Department"),
    ],
    "device_management": [
        ("view_device", "View Device"),
        ("add_device", "Add Device"),
        ("update_device", "Update Device"),
        ("delete_device", "Delete Device"),
        ("decommission_device", "Decommission Device"),
        ("restore_device", "Restore Device"),
    ],
    "device_assignments": [
        ("view_assignment", "View Device Assignment"),
        ("assign_device", "Assign Device"),
        ("return_device", "Return Device"),
        ("update_assignment", "Update Device Assignment"),
        ("delete_assignment", "Delete Device Assignment"),
    ],
    "repair_management": [
        ("view_repairs", "View Repairs"),
        ("request_repair", "Request Repair"),
        ("approve_repairs", "Approve Repairs"),
        ("start_repair", "Start Repair"),
        ("update_repair", "Update Repair"),
        ("complete_repair", "Complete Repair"),
    ],
    "inventory_management": [
        ("view_inventory", "View Inventory"),
        ("create_inventory_session", "Create Inventory Session"),
        ("verify_inventory", "Verify Inventory"),
        ("approve_inventory", "Approve Inventory"),
        ("close_inventory", "Close Inventory"),
    ],
    "audit_devices": [
        ("view_device_audit", "View Device Audit"),
    ],
    "system_audit_logs": [
        ("view_audit_logs", "View System Audit Logs"),
    ],
    "head_office_reports": [
        ("view_reports", "View Reports"),
        ("export_reports", "Export Reports"),
    ],
    "access_control": [
        ("view_access_control", "View Access Control"),
        ("add_role", "Create Role"),
        ("update_role", "Edit Role"),
        ("delete_role", "Delete Role"),
        ("assign_role", "Assign Role"),
        ("manage_permissions", "Manage Permission Structure"),
    ],
    "employee_self_service": [
        ("view_my_devices", "View My Devices"),
        ("submit_repair_request", "Submit Repair Request"),
        ("view_my_repair_requests", "View My Repair Requests"),
    ],
    "branch_operations": [
        ("view_branch_devices", "View Branch Devices"),
        ("view_branch_employees", "View Branch Employees"),
        ("participate_inventory_verification", "Participate Inventory Verification"),
        ("view_branch_reports", "View Branch Reports"),
    ],
    "technician_tasks": [
        ("view_technician_repairs", "View Technician Repairs"),
        ("diagnose_device_issue", "Diagnose Device Issue"),
        ("update_repair_progress", "Update Repair Progress"),
        ("mark_repair_completed", "Mark Repair Completed"),
    ],
}

DEFAULT_ROLE_PERMISSIONS = {
    "HEAD_OFFICE": "__all__",
    "BRANCH_MANAGER": [
        "view_branch_devices",
        "view_branch_employees",
        "participate_inventory_verification",
        "view_branch_reports",
        "view_device",
        "view_employee",
        "view_inventory",
        "verify_inventory",
        "approve_inventory",
        "view_my_devices",
        "submit_repair_request",
        "view_my_repair_requests",
    ],
    "TECHNICIAN": [
        "view_technician_repairs",
        "diagnose_device_issue",
        "update_repair_progress",
        "mark_repair_completed",
        "view_repairs",
        "start_repair",
        "update_repair",
        "complete_repair",
        "view_device",
        "view_my_devices",
        "submit_repair_request",
        "view_my_repair_requests",
    ],
    "EMPLOYEE": [
        "view_my_devices",
        "submit_repair_request",
        "view_my_repair_requests",
        "request_repair",
    ],
}

MENU_DEFINITIONS = [
    {
        "label": "Head Office",
        "icon": "feather-briefcase",
        "items": [
            ("Employee", "head_office_employees", "view_employee"),
            ("Branches", "head_office_branches", "view_branch"),
            ("Departments", "head_office_departments", "view_department"),
            ("Devices", "head_office_devices", "view_device"),
            ("Assignments", "head_office_assignments", "view_assignment"),
            ("Repairs", "head_office_repairs", "view_repairs"),
            ("Inventory", "head_office_inventory", "view_inventory"),
            ("Audit Device", "head_office_audit_device", "view_device_audit"),
            ("Audit Logs", "head_office_audit_logs", "view_audit_logs"),
            ("Reports", "head_office_reports", "view_reports"),
        ],
    },
    {
        "label": "Access Control",
        "icon": "feather-shield",
        "items": [
            ("Roles Management", "access_control_roles", "view_access_control"),
            ("Permissions Management", "access_control_permissions", "manage_permissions"),
            ("Role Assignment", "access_control_assignments", "assign_role"),
        ],
    },
    {
        "label": "Branch Manager",
        "icon": "feather-home",
        "items": [
            ("Branch Devices", "branch_devices", "view_branch_devices"),
            ("Branch Employees", "branch_employees", "view_branch_employees"),
            ("Inventory Verification", "branch_inventory_verification", "participate_inventory_verification"),
            ("Reports", "branch_reports", "view_branch_reports"),
        ],
    },
    {
        "label": "Technician Task",
        "icon": "feather-settings",
        "items": [
            ("Repairs", "technician_repairs", "view_technician_repairs"),
            ("In Progress Repairs", "technician_in_progress_repairs", "update_repair_progress"),
            ("Completed Repairs", "technician_completed_repairs", "mark_repair_completed"),
            ("Device Lookup", "technician_device_lookup", "diagnose_device_issue"),
            ("Repair History", "technician_repair_history", "view_technician_repairs"),
        ],
    },
    {
        "label": "Employee",
        "icon": "feather-user",
        "items": [
            ("My Devices", "employee_my_devices", "view_my_devices"),
            ("Request Repair", "employee_request_repair", "submit_repair_request"),
            ("Repair Requests", "employee_repair_requests", "view_my_repair_requests"),
        ],
    },
]


def all_permission_codenames():
    return [codename for permissions in PERMISSION_DEFINITIONS.values() for codename, _ in permissions]


def user_has_permission(user, codename):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.role == "HEAD_OFFICE":
        return True
    if getattr(user, "dynamic_role_id", None):
        return user.dynamic_role.permissions.filter(codename=codename).exists()

    role_permissions = DEFAULT_ROLE_PERMISSIONS.get(user.role, [])
    return role_permissions == "__all__" or codename in role_permissions


def get_user_permission_codenames(user):
    if not user or not user.is_authenticated:
        return []
    if user.is_superuser or user.role == "HEAD_OFFICE":
        return all_permission_codenames()
    if getattr(user, "dynamic_role_id", None):
        return list(user.dynamic_role.permissions.values_list("codename", flat=True))
    role_permissions = DEFAULT_ROLE_PERMISSIONS.get(user.role, [])
    if role_permissions == "__all__":
        return all_permission_codenames()
    return list(role_permissions)


def build_accessible_menu(user):
    menu = []
    for group in MENU_DEFINITIONS:
        items = [
            {"label": label, "url_name": url_name, "permission": permission}
            for label, url_name, permission in group["items"]
            if user_has_permission(user, permission)
        ]
        if items:
            menu.append({"label": group["label"], "icon": group["icon"], "items": items})
    return menu
