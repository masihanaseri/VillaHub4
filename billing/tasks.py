"""
توابع پس‌زمینه/دوره‌ای مربوط به Billing.

این پروژه فعلاً از Celery استفاده نمی‌کند (مطابق reservations/notifications/
gates که توابع ساده پایتون هستند)، بنابراین این توابع را می‌توان از طریق یک
management command یا cron صدا زد. در صورت اضافه شدن Celery در آینده، کافیست
دکوراتور @shared_task به هرکدام اضافه شود، مثلاً:

    CELERY_BEAT_SCHEDULE = {
        "billing-generate-invoices": {
            "task": "billing.tasks.generate_due_invoices",
            "schedule": crontab(hour=1, minute=0),
        },
        "billing-flag-overdue-invoices": {
            "task": "billing.tasks.flag_overdue_invoices",
            "schedule": crontab(hour=2, minute=0),
        },
        "billing-apply-automatic-penalties": {
            "task": "billing.tasks.apply_automatic_penalties",
            "schedule": crontab(hour=3, minute=0),
        },
    }
"""
import logging

from billing.models import Invoice, InvoiceStatus
from billing.services import InvoiceService

logger = logging.getLogger("billing.tasks")


def generate_due_invoices():
    """Runs BillingCycleService.run_due_cycles() using the real
    residence provider from the villas app."""
    from billing.services import BillingCycleService
    from villas.services import iter_billable_residences_for_cycle

    count = BillingCycleService.run_due_cycles(iter_billable_residences_for_cycle)
    logger.info("Generated %s invoice(s) from due billing cycles.", count)
    return count


def flag_overdue_invoices():
    qs = Invoice.objects.filter(
        status__in=[InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID]
    )
    flagged = 0
    for invoice in qs.iterator():
        before = invoice.status
        InvoiceService.mark_overdue_if_needed(invoice)
        if invoice.status != before:
            flagged += 1
    logger.info("Flagged %s invoice(s) as overdue.", flagged)
    return flagged


def apply_automatic_penalties(penalty_type="daily", value="10.00", reason="Late payment penalty"):
    """
    Applies one automatic penalty entry per currently-overdue invoice
    that doesn't already have an automatic penalty logged today.
    """
    from decimal import Decimal
    from django.utils import timezone

    applied = 0
    for invoice in Invoice.objects.filter(status=InvoiceStatus.OVERDUE).iterator():
        already_applied_today = invoice.penalties.filter(
            is_automatic=True, applied_at__date=timezone.localdate()
        ).exists()
        if already_applied_today:
            continue
        InvoiceService.apply_penalty(
            invoice,
            penalty_type=penalty_type,
            value=Decimal(value),
            reason=reason,
            is_automatic=True,
        )
        applied += 1
    logger.info("Applied automatic penalties to %s invoice(s).", applied)
    return applied
