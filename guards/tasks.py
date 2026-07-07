"""
توابع پس‌زمینه/دوره‌ای مربوط به Guard.

مطابق سایر اپ‌های پروژه (reservations/notifications) که فعلاً از Celery
استفاده نمی‌کنند، این‌ها توابع ساده پایتون هستند که می‌توان از طریق یک
management command یا cron صدا زد.
"""

import logging

from django.utils import timezone

from .models import Guard

from .services import GuardService

logger = logging.getLogger("guards")


def auto_close_stale_shifts(max_hours=16):
    """
    شیفت‌هایی که بیش از max_hours ساعت باز مانده‌اند (مثلاً نگهبان فراموش
    کرده خروج خود را ثبت کند) را به صورت خودکار می‌بندد.
    """

    threshold = timezone.now() - timezone.timedelta(hours=max_hours)

    stale_guards = Guard.objects.filter(
        shifts__ended_at__isnull=True,
        shifts__started_at__lt=threshold,
    ).distinct()

    count = 0

    for guard in stale_guards:

        GuardService.end_shift(
            guard=guard,
            performed_by=None,
        )

        count += 1

    logger.info(
        "auto_close_stale_shifts: %s شیفت بسته شد.",
        count,
    )

    return count


def deactivate_guards_of_inactive_townships():
    """
    نگهبانان متعلق به شهرک‌های غیرفعال را غیرفعال می‌کند.
    """

    guards = Guard.objects.filter(
        township__is_active=False,
        is_active=True,
    )

    count = 0

    for guard in guards:

        GuardService.deactivate(
            guard=guard,
            performed_by=None,
        )

        count += 1

    logger.info(
        "deactivate_guards_of_inactive_townships: %s نگهبان غیرفعال شد.",
        count,
    )

    return count
