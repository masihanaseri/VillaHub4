"""
توابع پس‌زمینه/گزارش‌گیری مربوط به AccessLog.

مطابق سایر اپ‌های پروژه، این‌ها توابع ساده پایتون هستند (بدون Celery) که
می‌توان از طریق management command یا cron صدا زد.
"""

import logging

from django.db.models import Count

from django.utils import timezone

from .models import AccessLog

logger = logging.getLogger("access_logs")


def daily_traffic_summary(township, date=None):
    """
    خلاصه ورود/خروج هر درب در یک روز مشخص (پیش‌فرض: امروز).
    خروجی برای داشبورد یا گزارش روزانه مدیر شهرک مناسب است.
    """

    target_date = date or timezone.localdate()

    queryset = AccessLog.objects.filter(
        township=township,
        occurred_at__date=target_date,
    )

    summary = (
        queryset.values(
            "gate_id",
            "gate__name",
            "direction",
        )
        .order_by(
            "gate_id",
            "direction",
        )
        .annotate(
            total=Count("id"),
        )
    )

    return list(summary)


def visitors_without_exit(township, older_than_hours=12):
    """
    مهمانانی که ورودشان ثبت شده اما بیش از older_than_hours ساعت هنوز
    خروجی برایشان ثبت نشده—برای هشدار به نگهبانی مفید است.
    """

    threshold = timezone.now() - timezone.timedelta(hours=older_than_hours)

    flagged = []

    for entry in AccessLog.objects.filter(
        township=township,
        direction=AccessLog.Direction.IN,
        visitor__isnull=False,
        occurred_at__lt=threshold,
    ).select_related("visitor"):

        has_later_exit = AccessLog.objects.filter(
            visitor=entry.visitor,
            direction=AccessLog.Direction.OUT,
            occurred_at__gt=entry.occurred_at,
        ).exists()

        if not has_later_exit:

            flagged.append(entry)

    logger.info(
        "visitors_without_exit: %s مهمان بدون خروج ثبت‌شده یافت شد.",
        len(flagged),
    )

    return flagged
