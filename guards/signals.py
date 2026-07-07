import logging

from django.db.models.signals import post_save

from django.dispatch import receiver

from .models import Guard

logger = logging.getLogger("guards")


@receiver(post_save, sender=Guard)
def guard_post_save(sender, instance, created, **kwargs):

    if created:

        logger.info(
            "نگهبان جدید ثبت شد: township=%s employee_code=%s",
            instance.township_id,
            instance.employee_code,
        )
