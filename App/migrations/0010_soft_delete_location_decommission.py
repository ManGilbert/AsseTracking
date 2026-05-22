from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("App", "0009_backfill_device_registered_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="branch",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="branch",
            name="deleted_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="branch_deleted_records", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="branch",
            name="deletion_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="branch",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="department",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="department",
            name="deleted_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="department_deleted_records", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="department",
            name="deletion_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="department",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="employee",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="employee",
            name="deleted_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="employee_deleted_records", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="employee",
            name="deletion_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="employee",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="device",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="device",
            name="deleted_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="device_deleted_records", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="device",
            name="deletion_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="device",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="device",
            name="decommission_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="device",
            name="decommission_reason",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="device",
            name="decommissioned_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="device",
            name="decommissioned_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="decommissioned_devices", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="device",
            name="last_location_before_decommission",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="device",
            name="previous_status_before_decommission",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="inventorysession",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="inventorysession",
            name="deleted_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="inventorysession_deleted_records", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="inventorysession",
            name="deletion_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="inventorysession",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="DeviceLocationHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("location_type", models.CharField(choices=[("HEAD_OFFICE", "Head Office"), ("BRANCH", "Branch"), ("EMPLOYEE", "Employee"), ("TECHNICIAN", "Head Office / Technician")], max_length=20)),
                ("location", models.CharField(max_length=255)),
                ("action", models.CharField(max_length=100)),
                ("status", models.CharField(blank=True, max_length=20)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("notes", models.TextField(blank=True)),
                ("device", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="location_history", to="App.device")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-timestamp"],
            },
        ),
    ]
