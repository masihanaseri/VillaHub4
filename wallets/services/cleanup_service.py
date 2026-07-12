import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..models import WalletTransaction
from .wallet_service import WalletService

logger = logging.getLogger("wallets.services")

DEFAULT_PENDING_TIMEOUT_MINUTES = 30


class CleanupService:

    @staticmethod
    def get_timeout_minutes():

        return getattr(
            settings,
            "WALLET_PENDING_TRANSACTION_TIMEOUT_MINUTES",
            DEFAULT_PENDING_TIMEOUT_MINUTES,
        )

    @staticmethod
    def expire_stale_pending_transactions():
        """
        Transitions any PENDING transaction older than the configured
        timeout to EXPIRED. Never deletes rows — expired transactions
        remain in the audit trail.

        Returns the number of transactions expired.
        """

        cutoff = timezone.now() - timezone.timedelta(
            minutes=CleanupService.get_timeout_minutes(),
        )

        stale_ids = list(
            WalletTransaction.objects.filter(
                status=WalletTransaction.TransactionStatus.PENDING,
                created_at__lt=cutoff,
            ).values_list("id", flat=True)
        )

        expired_count = 0

        for transaction_id in stale_ids:
            with transaction.atomic():
                stale_transaction = WalletTransaction.objects.select_for_update().get(
                    pk=transaction_id,
                )

                if stale_transaction.status != WalletTransaction.TransactionStatus.PENDING:
                    continue

                WalletService.fail_pending_transaction(
                    stale_transaction,
                    reason="Expired: no confirmation received within the timeout window.",
                    new_status=WalletTransaction.TransactionStatus.EXPIRED,
                )
                expired_count += 1

        if expired_count:
            logger.info(
                "wallet.transactions.expired",
                extra={"count": expired_count},
            )

        return expired_count
