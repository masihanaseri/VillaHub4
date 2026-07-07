"""
توابع پس‌زمینه/دوره‌ای مربوط به AccessPass و AccessLog.

مطابق سایر اپ‌های پروژه (reservations، gates، access_logs)، این پروژه
فعلاً از Celery استفاده نمی‌کند؛ این‌ها توابع ساده پایتون هستند که از
طریق یک management command یا cron صدا زده می‌شوند. در صورت اضافه شدن
Celery در آینده، کافی‌ست دکوراتور @shared_task به هرکدام اضافه شود.
"""

import logging

from django.db.models import Count

from django.utils import timezone

from .models import (
    AccessPass,
    AccessLog,
)

from .services import AccessControlService

logger = logging.getLogger("access_control")


def expire_passes_task():
    """
    کارت‌های تردد منقضی‌شده را به وضعیت EXPIRED تغییر می‌دهد.
    مناسب برای اجرای دوره‌ای (مثلاً هر ساعت).
    """

    count = AccessControlService.expire_passes()

    logger.info(
        "expire_passes_task: %s کارت تردد منقضی شد.",
        count,
    )

    return count


def passes_without_checkout(township=None, older_than_hours=12):
    """
    کارت‌هایی که ورودشان ثبت شده اما بیش از older_than_hours ساعت هنوز
    خروجی برایشان ثبت نشده—برای هشدار به نگهبانی/مدیر شهرک مفید است.
    """

    threshold = timezone.now() - timezone.timedelta(
        hours=older_than_hours,
    )

    queryset = AccessPass.objects.filter(
        status=AccessPass.Status.CHECKED_IN,
        checked_in_at__lt=threshold,
    ).select_related(
        "visitor",
        "gate",
    )

    if township is not None:

        queryset = queryset.filter(
            township=township,
        )

    flagged = list(queryset)

    logger.info(
        "passes_without_checkout: %s کارت بدون خروج ثبت‌شده یافت شد.",
        len(flagged),
    )

    return flagged


def daily_traffic_summary(township, date=None):
    """
    خلاصه ورود/خروج/رد شده هر درب در یک روز مشخص (پیش‌فرض: امروز).
    خروجی برای داشبورد یا گزارش روزانه مدیر شهرک مناسب است.
    """

    target_date = date or timezone.localdate()

    queryset = AccessLog.objects.filter(
        township=township,
        created_at__date=target_date,
    )

    summary = (
        queryset.values(
            "gate_id",
            "gate__name",
            "action",
        )
        .order_by(
            "gate_id",
            "action",
        )
        .annotate(
            total=Count("id"),
        )
    )

    return list(summary)


def bulk_expire_by_ids(access_pass_ids):
    """
    انقضای دستی مجموعه‌ای مشخص از کارت‌های تردد (مثلاً از طریق ابزار
    مدیریتی داخلی).
    """

    queryset = AccessPass.objects.filter(
        id__in=access_pass_ids,
        status__in=[
            AccessPass.Status.PENDING,
            AccessPass.Status.APPROVED,
        ],
    )

    count = queryset.update(
        status=AccessPass.Status.EXPIRED,
    )

    logger.info(
        "bulk_expire_by_ids: %s کارت تردد به‌صورت دستی منقضی شد.",
        count,
    )

    return count
