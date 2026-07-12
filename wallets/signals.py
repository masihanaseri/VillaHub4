import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import WalletTransaction

logger = logging.getLogger("wallets.audit")


@receiver(post_save, sender=WalletTransaction)
def wallet_transaction_saved(sender, instance, created, **kwargs):
    """
    Structured audit trail for every wallet transaction write. Kept
    deliberately side-effect free (no further DB writes) so it can
    never turn a read into an unexpected write or create a signal-vs-
    service double-write race; balance changes only ever happen inside
    the service layer that triggered this save.

    Extension point for: notifications, external accounting export,
    fraud/anomaly alerts.
    """

    logger.info(
        "wallet_transaction.saved",
        extra={
            "created": created,
            "internal_reference": instance.internal_reference,
            "wallet_id": instance.wallet_id,
            "status": instance.status,
            "transaction_type": instance.transaction_type,
            "amount": str(instance.amount),
        },
    )
