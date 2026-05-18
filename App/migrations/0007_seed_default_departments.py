from django.db import migrations

DEFAULT_DEPARTMENT_NAMES = [
    "Human Resources",
    "Finance",
    "Operations",
    "Information Technology",
    "Logistics",
    "Procurement",
    "Customer Service",
    "Maintenance",
]


def seed_default_departments(apps, schema_editor):
    Branch = apps.get_model("App", "Branch")
    Department = apps.get_model("App", "Department")

    for branch in Branch.objects.all():
        for name in DEFAULT_DEPARTMENT_NAMES:
            Department.objects.get_or_create(branch=branch, name=name)


def reverse_seed_default_departments(apps, schema_editor):
    Department = apps.get_model("App", "Department")
    Department.objects.filter(name__in=DEFAULT_DEPARTMENT_NAMES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0006_inventoryitem_pending_status"),
    ]

    operations = [
        migrations.RunPython(seed_default_departments, reverse_seed_default_departments),
    ]
