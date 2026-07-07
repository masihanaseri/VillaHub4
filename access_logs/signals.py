import logging

from django.db.models.signals import post_save

from django.dispatch import receiver

from .models import AccessLog

logger = logging.getLogger("access_logs")


@receiver(post_save, sender=AccessLog)
def access_log_post_save(sender, instance, created, **kwargs):

    if not created:

        return

    logger.info(
        "تردد ثبت شد: township=%s gate=%s direction=%s subject=%s",
        instance.township_id,
        instance.gate_id,
        instance.direction,
        instance.subject_display,
    )
