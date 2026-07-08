from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.models import Notification

from .models import MaintenanceRequest


@receiver(
    post_save,
    sender=MaintenanceRequest,
)
def maintenance_created(
    sender,
    instance,
    created,
    **kwargs,
):

    if not created:
        return

    Notification.objects.create(
        recipient=instance.created_by,
        township=instance.township,
        created_by=instance.created_by,
        title="درخواست تعمیرات ثبت شد",
        message=instance.title,
        notification_type=Notification.NotificationType.SYSTEM,
    )