from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0005_employee_employee_id_user_must_change_password_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inventoryitem",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("VERIFIED", "Verified"),
                    ("MISSING", "Missing"),
                    ("EXTRA", "Extra"),
                    ("IN_REPAIR", "In Repair"),
                    ("RETURNED_HEAD_OFFICE", "Returned to Head Office"),
                ],
                default="PENDING",
                max_length=30,
            ),
        ),
    ]
