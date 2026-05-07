from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0003_inventoryitem_extra_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="device",
            name="status",
            field=models.CharField(
                choices=[
                    ("AVAILABLE", "Available"),
                    ("ASSIGNED", "Assigned"),
                    ("PENDING_RETURN", "Pending Return"),
                    ("IN_REPAIR", "In Repair"),
                    ("COMPLETED", "Completed"),
                    ("REPAIRED", "Repaired"),
                    ("MISSING", "Missing"),
                    ("RETIRED", "Retired"),
                ],
                default="AVAILABLE",
                max_length=20,
            ),
        ),
    ]

