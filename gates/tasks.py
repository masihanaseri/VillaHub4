"""
توابع پس‌زمینه/دوره‌ای مربوط به Gate.

این پروژه فعلاً از Celery استفاده نمی‌کند (مطابق reservations/notifications که
توابع ساده پایتون هستند)، بنابراین این توابع را می‌توان از طریق یک
management command یا cron صدا زد. در صورت اضافه شدن Celery در آینده،
کافیست دکوراتور @shared_task را به هرکدام اضافه کرد.
"""

import logging

from .models import Gate

from .services import GateService

logger = logging.getLogger("gates")


def deactivate_gates_of_inactive_townships():
    """
    درب‌های متعلق به شهرک‌های غیرفعال را غیرفعال می‌کند.
    مناسب برای اجرای دوره‌ای شبانه.
    """

    gates = Gate.objects.filter(
        township__is_active=False,
        is_active=True,
    ).select_related(
        "township",
    )

    count = 0

    for gate in gates:

        GateService.deactivate(
            gate=gate,
        )

        count += 1

    logger.info(
        "deactivate_gates_of_inactive_townships: %s درب غیرفعال شد.",
        count,
    )

    return count


def gates_without_coordinates_report(township=None):
    """
    گزارش درب‌هایی که هنوز مختصات جغرافیایی ندارند؛
    برای هشدار به مدیر شهرک هنگام راه‌اندازی نقشه دربها کاربرد دارد.
    """

    queryset = Gate.objects.filter(
        latitude__isnull=True,
    )

    if township is not None:

        queryset = queryset.filter(
            township=township,
        )

    return list(
        queryset.values_list(
            "id",
            "code",
            "name",
        ),
    )


def bulk_activate(gate_ids):

    gates = Gate.objects.filter(
        id__in=gate_ids,
        is_active=False,
    )

    count = 0

    for gate in gates:

        GateService.activate(
            gate=gate,
        )

        count += 1

    return count


def bulk_deactivate(gate_ids):

    gates = Gate.objects.filter(
        id__in=gate_ids,
        is_active=True,
    )

    count = 0

    for gate in gates:

        GateService.deactivate(
            gate=gate,
        )

        count += 1

    return count
