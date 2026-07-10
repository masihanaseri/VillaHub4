from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import WalletTransaction


@receiver(post_save, sender=WalletTransaction)
def wallet_transaction_created(
    sender,
    instance,
    created,
    **kwargs,
):

    if not created:
        return

    # Future:
    # - Send Notification
    # - Create Accounting Entry
    # - Register Commission
    # - Audit Log

    pass