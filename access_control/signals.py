import logging

from django.db.models.signals import (
    pre_save,
    post_save,
)

from django.dispatch import receiver

from .models import AccessPass

logger = logging.getLogger("access_control")


@receiver(pre_save, sender=AccessPass)
def access_pass_pre_save(sender, instance, **kwargs):
    """
    قبل از ذخیره، تغییر وضعیت را روی خود instance علامت می‌زند تا در
    post_save بتوان تشخیص داد که status تغییر کرده یا نه.
    """

    if instance.pk is None:

        instance._status_changed = False

        instance._previous_status = None

        return

    try:

        previous = AccessPass.objects.only("status").get(pk=instance.pk)

    except AccessPass.DoesNotExist:

        instance._status_changed = False

        instance._previous_status = None

        return

    instance._status_changed = previous.status != instance.status

    instance._previous_status = previous.status


@receiver(post_save, sender=AccessPass)
def access_pass_post_save(sender, instance, created, **kwargs):

    if created:

        logger.info(
            "کارت تردد جدید ایجاد شد: township=%s visitor=%s status=%s",
            instance.township_id,
            instance.visitor_id,
            instance.status,
        )

        return

    if getattr(instance, "_status_changed", False):

        logger.info(
            "وضعیت کارت تردد تغییر کرد: township=%s visitor=%s %s -> %s",
            instance.township_id,
            instance.visitor_id,
            getattr(instance, "_previous_status", "?"),
            instance.status,
        )
