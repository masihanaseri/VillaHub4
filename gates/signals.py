import logging

from django.db.models.signals import post_save, pre_save

from django.dispatch import receiver

from .models import Gate

logger = logging.getLogger("gates")


@receiver(pre_save, sender=Gate)
def gate_pre_save(sender, instance, **kwargs):
    """
    قبل از ذخیره، تغییر وضعیت فعال/غیرفعال را روی خود instance علامت می‌زند
    تا در post_save بتوان تشخیص داد که is_active تغییر کرده یا نه.
    """

    if instance.pk is None:

        instance._is_active_changed = False

        return

    try:

        previous = Gate.objects.only("is_active").get(pk=instance.pk)

    except Gate.DoesNotExist:

        instance._is_active_changed = False

        return

    instance._is_active_changed = (
        previous.is_active != instance.is_active
    )


@receiver(post_save, sender=Gate)
def gate_post_save(sender, instance, created, **kwargs):

    if created:

        logger.info(
            "درب جدید ایجاد شد: township=%s code=%s name=%s",
            instance.township_id,
            instance.code,
            instance.name,
        )

        return

    if getattr(instance, "_is_active_changed", False):

        status = "فعال" if instance.is_active else "غیرفعال"

        logger.info(
            "وضعیت درب تغییر کرد: township=%s code=%s status=%s",
            instance.township_id,
            instance.code,
            status,
        )
