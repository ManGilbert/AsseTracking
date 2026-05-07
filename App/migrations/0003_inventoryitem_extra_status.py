from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0002_remove_auditlog_device_remove_device_department_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inventoryitem",
            name="status",
            field=models.CharField(
                choices=[
                    ("VERIFIED", "Verified"),
                    ("MISSING", "Missing"),
                    ("EXTRA", "Extra"),
                ],
                max_length=10,
            ),
        ),
    ]

