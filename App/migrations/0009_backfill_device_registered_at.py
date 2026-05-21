from django.db import migrations


def backfill_device_registered_at(apps, schema_editor):
    Device = apps.get_model("App", "Device")
    AuditLog = apps.get_model("App", "AuditLog")

    created_logs = (
        AuditLog.objects.filter(model_name="Device", action="DEVICE_CREATED")
        .exclude(object_id__isnull=True)
        .order_by("timestamp")
    )
    created_by_device = {}
    for log in created_logs:
        created_by_device.setdefault(log.object_id, log.timestamp)

    devices = Device.objects.filter(id__in=created_by_device.keys())
    for device in devices:
        device.registered_at = created_by_device[device.id]
        device.save(update_fields=["registered_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0008_device_registered_at"),
    ]

    operations = [
        migrations.RunPython(backfill_device_registered_at, migrations.RunPython.noop),
    ]
