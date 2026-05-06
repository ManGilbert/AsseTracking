from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Branch, Device, Employee, InventorySession, RepairRequest, User
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

    def test_employee_create_generates_login_credentials(self):
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

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        employee = Employee.objects.get(id=response.data["id"])
        self.assertIsNotNone(employee.user)
        self.assertEqual(response.data["generated_username"], employee.user.username)
        self.assertEqual(response.data["generated_email"], employee.user.email)
        self.assertEqual(response.data["default_password"], DEFAULT_EMPLOYEE_PASSWORD)
        self.assertTrue(employee.user.check_password(DEFAULT_EMPLOYEE_PASSWORD))

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
