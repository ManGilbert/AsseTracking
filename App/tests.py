from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Branch, Device, DeviceAssignment, Employee, InventorySession, RepairRequest, User
from .serializers import DEFAULT_EMPLOYEE_PASSWORD


class HeadOfficeWorkflowApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.head_office = User.objects.create_user(
            username="head.office",
            email="head.office@example.com",
            password="Password123!",
            role="HEAD_OFFICE",
        )
        self.client.force_authenticate(self.head_office)
        self.branch = Branch.objects.create(name="Main Branch", location="City")

    def test_employee_create_requires_and_uses_login_credentials(self):
        response = self.client.post(
            "/api/employees/",
            {
                "full_name": "Jane Worker",
                "position": "Analyst",
                "branch": self.branch.id,
                "hire_date": "2026-05-06",
                "login_username": "jane.worker",
                "login_email": "jane.worker@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        employee = Employee.objects.get(id=response.data["id"])
        self.assertIsNotNone(employee.user)
        self.assertEqual(employee.user.username, "jane.worker")
        self.assertEqual(employee.user.email, "jane.worker@example.com")
        self.assertEqual(response.data["default_password"], DEFAULT_EMPLOYEE_PASSWORD)
        self.assertTrue(employee.user.check_password(DEFAULT_EMPLOYEE_PASSWORD))

    def test_employee_create_rejects_missing_login_credentials(self):
        response = self.client.post(
            "/api/employees/",
            {
                "full_name": "Jane Worker",
                "position": "Analyst",
                "branch": self.branch.id,
                "hire_date": "2026-05-06",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("login_username", response.data)
        self.assertIn("login_email", response.data)

    def test_branch_manager_registration_assigns_branch_manager(self):
        response = self.client.post(
            "/api/employees/",
            {
                "full_name": "Manager One",
                "position": "Branch Manager",
                "branch": self.branch.id,
                "hire_date": "2026-05-06",
                "login_username": "manager.one",
                "login_email": "manager.one@example.com",
                "login_role": "BRANCH_MANAGER",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.branch.refresh_from_db()
        employee = Employee.objects.get(id=response.data["id"])
        self.assertEqual(employee.user.role, "BRANCH_MANAGER")
        self.assertEqual(self.branch.manager, employee)

    def test_assignment_requires_device_and_employee_same_branch(self):
        other_branch = Branch.objects.create(name="Other Branch", location="Other")
        employee_user = User.objects.create_user(
            username="employee.two",
            email="employee.two@example.com",
            password="Password123!",
            role="EMPLOYEE",
        )
        employee = Employee.objects.create(
            user=employee_user,
            full_name="Employee Two",
            position="Clerk",
            branch=other_branch,
            hire_date="2026-05-06",
        )
        device = Device.objects.create(
            device_type="Laptop",
            brand="Dell",
            model="Latitude",
            serial_number="SN-BRANCH-1",
            company_tag="TAG-BRANCH-1",
            status="AVAILABLE",
            assigned_branch=self.branch,
            location_type="BRANCH",
            current_location=self.branch.name,
        )

        response = self.client.post(
            "/api/assignments/",
            {"device_id": device.id, "employee_id": employee.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("only be assigned to employees from that branch", response.data["error"])

    def test_device_with_assignment_history_cannot_be_deleted(self):
        employee_user = User.objects.create_user(
            username="employee.history",
            email="employee.history@example.com",
            password="Password123!",
            role="EMPLOYEE",
        )
        employee = Employee.objects.create(
            user=employee_user,
            full_name="Employee History",
            position="Clerk",
            branch=self.branch,
            hire_date="2026-05-06",
        )
        device = Device.objects.create(
            device_type="Laptop",
            brand="Dell",
            model="Latitude",
            serial_number="SN-HISTORY-1",
            company_tag="TAG-HISTORY-1",
            status="AVAILABLE",
        )
        DeviceAssignment.objects.create(
            device=device,
            employee=employee,
            branch=self.branch,
            assigned_by=self.head_office,
        )

        response = self.client.delete(f"/api/devices/{device.id}/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Device.objects.filter(id=device.id).exists())

    def test_head_office_can_create_approve_and_reject_repairs(self):
        employee_user = User.objects.create_user(
            username="employee.one",
            email="employee.one@example.com",
            password="Password123!",
            role="EMPLOYEE",
        )
        employee = Employee.objects.create(
            user=employee_user,
            full_name="Employee One",
            position="Clerk",
            branch=self.branch,
            hire_date="2026-05-06",
        )
        device = Device.objects.create(
            device_type="Laptop",
            brand="Dell",
            model="Latitude",
            serial_number="SN-REPAIR-1",
            company_tag="TAG-REPAIR-1",
            status="ASSIGNED",
            assigned_employee=employee,
            assigned_branch=self.branch,
            location_type="EMPLOYEE",
            current_location="Main Branch - Employee One",
        )

        create_response = self.client.post(
            "/api/repair-requests/",
            {
                "device_id": device.id,
                "employee_id": employee.id,
                "issue_description": "Screen flickers",
                "priority": "HIGH",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        approve_response = self.client.post(
            f"/api/repair-requests/{create_response.data['id']}/approve/",
            {},
            format="json",
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data["status"], "APPROVED")

        second_request = RepairRequest.objects.create(
            device=device,
            employee=employee,
            issue_description="Keyboard sticks",
            priority="NORMAL",
        )
        reject_response = self.client.post(
            f"/api/repair-requests/{second_request.id}/reject/",
            {},
            format="json",
        )
        self.assertEqual(reject_response.status_code, status.HTTP_200_OK)
        self.assertEqual(reject_response.data["status"], "REJECTED")

    def test_head_office_can_approve_inventory_session(self):
        create_response = self.client.post(
            "/api/inventory-sessions/",
            {"branch_id": self.branch.id},
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        approve_response = self.client.post(
            f"/api/inventory-sessions/{create_response.data['id']}/approve_head_office/",
            {},
            format="json",
        )

        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertTrue(approve_response.data["approved_by_head_office"])
        self.assertIsNotNone(InventorySession.objects.get(id=create_response.data["id"]).end_date)
