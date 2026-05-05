"""
Django signals for automatic audit logging.

Automatically creates audit log entries for model changes.
This is optional but recommended for tracking all system changes.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import (
    Device,
    DeviceAssignment,
    RepairRequest,
    InventoryItem,
    AuditLog,
)


@receiver(post_save, sender=Device)
def audit_device_save(sender, instance, created, **kwargs):
    """Log device creation or updates."""
    if created:
        AuditLog.objects.create(
            action="DEVICE_CREATED",
            model_name="Device",
            object_id=instance.id,
            details=f"Device {instance.company_tag} created",
        )


@receiver(post_delete, sender=Device)
def audit_device_delete(sender, instance, **kwargs):
    """Log device deletion."""
    AuditLog.objects.create(
        action="DEVICE_DELETED",
        model_name="Device",
        object_id=instance.id,
        details=f"Device {instance.company_tag} deleted",
    )


@receiver(post_save, sender=InventoryItem)
def audit_inventory_item_save(sender, instance, created, **kwargs):
    """Log inventory item changes."""
    if not created:
        AuditLog.objects.create(
            action="INVENTORY_ITEM_UPDATED",
            model_name="InventoryItem",
            object_id=instance.id,
            details=f"Inventory item status changed to {instance.status}",
        )
