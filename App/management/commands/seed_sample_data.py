import random
import time
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import OperationalError, connections, transaction
from django.utils import timezone

from App.models import (
    Branch,
    Department,
    Employee,
    User,
    Device,
    DeviceAssignment,
    RepairRequest,
    RepairLog,
    InventorySession,
    InventoryItem,
)
from App.serializers import DEFAULT_EMPLOYEE_PASSWORD


class Command(BaseCommand):
    help = (
        "Seed sample Rwandan-style employees, devices, repairs, returned assignments, "
        "and an inventory session for the Nyarugenge branch."
    )

    def handle(self, *args, **options):
        connections.close_all()
        self.stdout.write("Starting sample data seeding...")

        for attempt in range(3):
            try:
                with transaction.atomic():
                    self.head_office_user = self._get_or_create_head_office_user()
                    self.branches = {branch.name: branch for branch in Branch.objects.all()}

                    if len(self.branches) != 4:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Expected 4 branches, found {len(self.branches)}. Sample data will still be created for existing branches."
                            )
                        )

                    self.department_map = self._prepare_departments()
                    self.employee_users = self._create_employees()
                    self.devices = self._create_devices_for_employees()
                    self._create_returned_assignments()
                    self._create_repair_requests()
                    self._create_inventory_session()

                    self.stdout.write(self.style.SUCCESS("Sample data seeding complete."))
                break
            except OperationalError as exc:
                self.stderr.write(
                    f"Database lock detected on attempt {attempt + 1}. Retrying..."
                )
                if attempt == 2:
                    raise
                time.sleep(5)
                connections.close_all()

    def _get_or_create_head_office_user(self):
        user, created = User.objects.get_or_create(
            username="head.office",
            defaults={
                "email": "head.office@asset.ac.rw",
                "role": "HEAD_OFFICE",
                "is_staff": True,
                "is_superuser": False,
            },
        )
        if created:
            user.set_password(DEFAULT_EMPLOYEE_PASSWORD)
            user.save()
            self.stdout.write("Created Head Office user head.office@asset.ac.rw")
        return user

    def _prepare_departments(self):
        department_map = {}
        for branch_name, branch in self.branches.items():
            departments = list(branch.departments.all())
            if not departments:
                raise ValueError(f"Branch {branch_name} has no departments.")
            department_map[branch_name] = departments
        return department_map

    def _get_next_identity(self, seq_name, offset=0):
        if not hasattr(self, "identity_counters"):
            self.identity_counters = {}
        self.identity_counters.setdefault(seq_name, 0)
        self.identity_counters[seq_name] += 1 + offset
        return self.identity_counters[seq_name]

    def _make_unique_username_email(self, last_name):
        base = last_name.lower().replace(" ", "")
        candidate = base
        count = 1
        while User.objects.filter(username=candidate).exists() or User.objects.filter(email=f"{candidate}@asset.ac.rw").exists():
            count += 1
            candidate = f"{base}{count}"
        return candidate, f"{candidate}@asset.ac.rw"

    def _create_employees(self):
        sample_names = [
            ("Jean", "Uwimana"),
            ("Eric", "Niyonzima"),
            ("Aline", "Habimana"),
            ("Clement", "Mugisha"),
            ("Alice", "Mukamana"),
            ("Samuel", "Niyonsaba"),
            ("Fabrice", "Karangwa"),
            ("Sandrine", "Uwase"),
            ("Patrice", "Manzi"),
            ("Jeanne", "Umutesi"),
            ("Aimable", "Niyibimenya"),
            ("Innocent", "Uwera"),
            ("Divine", "Niyonzima"),
            ("Chantal", "Nyiransabimana"),
            ("Antoine", "Mukamana"),
            ("Eric", "Nsengiyumva"),
            ("Fiona", "Bizimana"),
            ("Kevin", "Nkurunziza"),
            ("Patricia", "Tuyishime"),
            ("Alex", "Rusanganwa"),
            ("Celine", "Nyiranshuti"),
            ("Jean Pierre", "Munyaneza"),
            ("Therese", "Ndayambaje"),
            ("Alphonse", "Nshimiyimana"),
            ("Leocadie", "Murekatete"),
            ("Emmanuel", "Ndagijimana"),
            ("Eunice", "Mukantwari"),
            ("Dieudonne", "Ishimwe"),
            ("Liliane", "Irakoze"),
            ("Fideline", "Mukankusi"),
            ("Pascal", "Munyanganizi"),
            ("Rachel", "Uwitonze"),
            ("Silas", "Ntabona"),
            ("Olivia", "Nshuti"),
            ("Damas", "Mukarubuga"),
            ("Claudine", "Gasore"),
            ("Benedict", "Munyaneza"),
            ("Ester", "Ndayisaba"),
            ("Valens", "Hirwa"),
            ("Josiane", "Irakoze"),
            ("Nadine", "Umwali"),
            ("Fabrice", "Ntawukuriryayo"),
            ("Denise", "Mukamurera"),
            ("Yves", "Byiringiro"),
            ("Gladys", "Nyirahabineza"),
            ("Samuel", "Ngabo"),
            ("Martha", "Niyibizi"),
            ("Ibrahim", "Uwayezu"),
            ("Esther", "Munyabugingo"),
            ("Claude", "Mukashema"),
            ("Ariane", "Niyonzima"),
            ("Patrick", "Nsabimana"),
        ]
        random.shuffle(sample_names)

        branch_config = {
            "Kigali": {"count": 13, "technicians": 3},
            "Kicukiro": {"count": 10, "technicians": 1},
            "Gasabo": {"count": 10, "technicians": 1},
            "Nyarugenge": {"count": 10, "technicians": 1},
        }

        created_users = []
        employee_users = []
        for branch_name, config in branch_config.items():
            branch = self.branches.get(branch_name)
            if not branch:
                self.stdout.write(self.style.WARNING(f"Branch {branch_name} not found, skipping."))
                continue

            departments = self.department_map[branch_name]
            branch_code = branch_name[:3].upper()
            name_index = 0

            # create manager first
            manager_first, manager_last = sample_names[name_index]
            name_index += 1
            manager_username, manager_email = self._make_unique_username_email(manager_last)
            manager_user = User.objects.create_user(
                username=manager_username,
                email=manager_email,
                password=DEFAULT_EMPLOYEE_PASSWORD,
                role="BRANCH_MANAGER",
            )
            manager_user.must_change_password = True
            manager_user.save(update_fields=["must_change_password"])
            manager = Employee.objects.create(
                user=manager_user,
                employee_id=f"{branch_code}-MGR-001",
                full_name=f"{manager_first} {manager_last}",
                position="Branch Manager",
                branch=branch,
                department=departments[0],
                hire_date=timezone.now().date() - timedelta(days=30),
            )
            branch.manager = manager
            branch.save(update_fields=["manager"])
            created_users.append(manager_user)
            employee_users.append(manager)

            technician_count = config["technicians"]
            total_count = config["count"]
            remaining = total_count - 1
            technician_names = []
            for _ in range(technician_count):
                if name_index >= len(sample_names):
                    raise ValueError("Sample name list exhausted.")
                technician_names.append(sample_names[name_index])
                name_index += 1

            for i in range(remaining):
                if name_index >= len(sample_names):
                    raise ValueError("Sample name list exhausted.")
                first_name, last_name = sample_names[name_index]
                name_index += 1
                role = "TECHNICIAN" if i < technician_count else "EMPLOYEE"
                position = "Technician" if role == "TECHNICIAN" else "Asset Officer"
                username, email = self._make_unique_username_email(last_name)
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=DEFAULT_EMPLOYEE_PASSWORD,
                    role=role,
                )
                user.must_change_password = True
                user.save(update_fields=["must_change_password"])
                department = departments[i % len(departments)]
                employee = Employee.objects.create(
                    user=user,
                    employee_id=f"{branch_code}-{i+2:03d}",
                    full_name=f"{first_name} {last_name}",
                    position=position,
                    branch=branch,
                    department=department,
                    hire_date=timezone.now().date() - timedelta(days=15 + i),
                )
                created_users.append(user)
                employee_users.append(employee)

        self.stdout.write(self.style.SUCCESS(f"Created {len(employee_users)} branch employees."))
        return employee_users

    def _create_devices_for_employees(self):
        brands = {
            "Laptop": [("HP", "ProBook 450"), ("Dell", "Latitude 3420"), ("Lenovo", "ThinkPad E14")],
            "Desktop computer": [("Dell", "OptiPlex 3090"), ("HP", "EliteDesk 800"), ("Lenovo", "V50")],
            "Printer": [("Brother", "HL-L2390DW"), ("HP", "LaserJet Pro MFP"), ("Canon", "ImageCLASS LBP6030w")],
        }
        assigned_devices = []
        available_devices = []
        device_index = 1

        for employee in self.employee_users:
            if employee.user.role == "BRANCH_MANAGER":
                device_type = "Printer"
            elif employee.user.role == "TECHNICIAN":
                device_type = random.choice(["Laptop", "Desktop computer"])
            else:
                device_type = random.choice(["Laptop", "Desktop computer"])

            brand, model = random.choice(brands[device_type])
            branch_code = employee.branch.name[:3].upper()
            tag_id = f"{branch_code}-DEV-{device_index:03d}"
            serial = f"SN-{branch_code}-{device_index:05d}"
            device_index += 1
            device = Device.objects.create(
                device_type=device_type,
                brand=brand,
                model=model,
                serial_number=serial,
                company_tag=tag_id,
                purchase_date=timezone.now().date() - timedelta(days=90 + device_index),
                warranty_expiry=timezone.now().date() + timedelta(days=365),
                status="ASSIGNED",
                assigned_employee=employee,
                assigned_branch=employee.branch,
                location_type="EMPLOYEE",
                current_location=f"{employee.branch.name} - {employee.full_name}",
                condition_notes="Assigned during sample data seeding.",
            )
            DeviceAssignment.objects.create(
                device=device,
                employee=employee,
                branch=employee.branch,
                assigned_by=self.head_office_user,
                assigned_date=timezone.now() - timedelta(days=random.randint(1, 15)),
                condition_on_issue="Device in good condition on issue.",
            )
            assigned_devices.append(device)

        for index in range(8):
            device_type = random.choice(["Laptop", "Desktop computer"])
            if index < 2:
                device_type = "Printer"
            brand, model = random.choice(brands[device_type])
            tag_id = f"AVAIL-DEV-{index+1:03d}"
            serial = f"SN-AVAIL-{index+1:05d}"
            device = Device.objects.create(
                device_type=device_type,
                brand=brand,
                model=model,
                serial_number=serial,
                company_tag=tag_id,
                purchase_date=timezone.now().date() - timedelta(days=120 + index),
                warranty_expiry=timezone.now().date() + timedelta(days=280),
                status="AVAILABLE",
                assigned_employee=None,
                assigned_branch=None,
                location_type="HEAD_OFFICE",
                current_location="Head Office",
                condition_notes="Available unassigned device.",
            )
            available_devices.append(device)

        self.assigned_devices = assigned_devices
        self.available_devices = available_devices
        self.stdout.write(self.style.SUCCESS(f"Created {len(assigned_devices)} assigned devices and {len(available_devices)} available devices."))
        return assigned_devices + available_devices

    def _create_returned_assignments(self):
        returned_devices = self.available_devices[:3]
        returned_assignments = []
        for index, device in enumerate(returned_devices, start=1):
            branch = list(self.branches.values())[index % len(self.branches)]
            employee = Employee.objects.filter(branch=branch, status="ACTIVE").first()
            if not employee:
                continue
            assignment = DeviceAssignment.objects.create(
                device=device,
                employee=employee,
                branch=branch,
                assigned_by=self.head_office_user,
                assigned_date=timezone.now() - timedelta(days=30 + index),
                returned_date=timezone.now() - timedelta(days=10 + index),
                received_by=self.head_office_user,
                condition_on_issue="Device issued before return.",
                condition_on_return="Device returned in good condition.",
            )
            device.status = "AVAILABLE"
            device.assigned_employee = None
            device.assigned_branch = None
            device.location_type = "HEAD_OFFICE"
            device.current_location = "Head Office"
            device.save(update_fields=["status", "assigned_employee", "assigned_branch", "location_type", "current_location"])
            returned_assignments.append(assignment)

        self.stdout.write(self.style.SUCCESS(f"Created {len(returned_assignments)} returned device assignments."))
        return returned_assignments

    def _create_repair_requests(self):
        if not self.assigned_devices:
            self.stdout.write(self.style.WARNING("No assigned devices available to create repairs."))
            return

        technician_users = list(User.objects.filter(role="TECHNICIAN"))
        if not technician_users:
            technician_users = [self.head_office_user]

        repair_statuses = [
            ("PENDING", "Battery issue and slow performance."),
            ("APPROVED", "Network adapter not detected."),
            ("IN_PROGRESS", "Screen flickers intermittently."),
            ("COMPLETED", "Printer paper jam and error light."),
        ]

        created = 0
        for device in self.assigned_devices[:10]:
            repair_status, issue = repair_statuses[created % len(repair_statuses)]
            assignment_employee = device.assigned_employee
            if not assignment_employee:
                continue

            repair_request = RepairRequest.objects.create(
                device=device,
                employee=assignment_employee,
                issue_description=issue,
                priority="NORMAL",
                status=repair_status,
                request_date=timezone.now() - timedelta(days=5 - created),
                approved_by=self.head_office_user if repair_status in ["APPROVED", "IN_PROGRESS", "COMPLETED"] else None,
            )

            if repair_status in ["APPROVED", "IN_PROGRESS"]:
                device.status = "IN_REPAIR"
                device.save(update_fields=["status"])
            elif repair_status == "COMPLETED":
                device.status = "REPAIRED"
                device.save(update_fields=["status"])
                RepairLog.objects.create(
                    repair_request=repair_request,
                    technician=random.choice(technician_users),
                    notes="Repair completed successfully with replacement parts.",
                    parts_used="Power cable, fuser unit",
                    start_date=timezone.now() - timedelta(days=3 + created),
                    completed_date=timezone.now() - timedelta(days=1 + created),
                )

            created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} repair requests."))

    def _create_inventory_session(self):
        nyarugenge = self.branches.get("Nyarugenge")
        if not nyarugenge:
            self.stdout.write(self.style.WARNING("Nyarugenge branch not found, skipping inventory session."))
            return

        session = InventorySession.objects.create(
            branch=nyarugenge,
            start_date=timezone.now() - timedelta(days=7),
            end_date=timezone.now() - timedelta(days=5),
            created_by=self.head_office_user,
            approved_by_branch=True,
            approved_by_head_office=True,
        )

        devices = list(Device.objects.filter(assigned_branch=nyarugenge)[:4]) + self.available_devices[:2]
        statuses = ["VERIFIED", "MISSING", "EXTRA", "PENDING", "VERIFIED", "RETURNED_HEAD_OFFICE"]
        for device, status in zip(devices, statuses):
            InventoryItem.objects.create(
                session=session,
                device=device,
                status=status,
                comment=f"Sample inventory item marked {status}.",
            )

        self.stdout.write(self.style.SUCCESS("Created Nyarugenge inventory session and inventory items."))
