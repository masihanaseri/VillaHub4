"""
Signals are kept minimal and dumb on purpose: they only recompute
derived state (invoice totals) when child rows change directly in the
admin (bypassing services). All *business* actions - issuing an
invoice, recording a payment, applying a penalty - already call
InvoiceService.recalculate_totals() and NotificationDispatcher
themselves, so signals must not duplicate notification dispatch or
they would fire twice.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from billing.models import InvoiceItem, Discount, Penalty


def _recalculate(invoice):
    from billing.services import InvoiceService

    if invoice_id := getattr(invoice, "id", None):
        InvoiceService.recalculate_totals(invoice)


@receiver(post_save, sender=InvoiceItem)
@receiver(post_delete, sender=InvoiceItem)
def invoice_item_changed(sender, instance, **kwargs):
    _recalculate(instance.invoice)


@receiver(post_save, sender=Discount)
@receiver(post_delete, sender=Discount)
def discount_changed(sender, instance, **kwargs):
    _recalculate(instance.invoice)


@receiver(post_save, sender=Penalty)
@receiver(post_delete, sender=Penalty)
def penalty_changed(sender, instance, **kwargs):
    _recalculate(instance.invoice)
