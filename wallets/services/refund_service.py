"""
Centralizes every refund path so they all share the same atomic,
audited, idempotent core: credit the wallet, mark the originating
transaction REFUNDED, and record who/why.
"""

import logging

from django.db import transaction
from django.utils import timezone

from ..models import TransactionType, Wallet, WalletTransaction
from .wallet_service import WalletService, _to_decimal

logger = logging.getLogger("wallets.services")


class RefundError(Exception):
    pass


class RefundService:

    @staticmethod
    @transaction.atomic
    def _refund_core(wallet, amount, description, source_transaction=None,
                      metadata=None):

        amount = _to_decimal(amount)

        if source_transaction is not None:

            locked_source = (
                WalletTransaction.objects.select_for_update().get(
                    pk=source_transaction.pk,
                )
            )

            if locked_source.status != WalletTransaction.TransactionStatus.SUCCESS:
                raise RefundError(
                    "Only a SUCCESS transaction can be refunded."
                )

            if not locked_source.can_transition_to(
                WalletTransaction.TransactionStatus.REFUNDED,
            ):
                raise RefundError(
                    f"Transaction {locked_source.internal_reference} cannot be "
                    "refunded again."
                )

        refund_transaction = WalletService.deposit(
            wallet=wallet,
            amount=amount,
            description=description,
            transaction_type=TransactionType.REFUND,
            metadata=metadata or {},
        )

        if source_transaction is not None:
            locked_source.status = WalletTransaction.TransactionStatus.REFUNDED
            locked_source.full_clean()
            locked_source.save()

        logger.info(
            "refund.issued",
            extra={
                "wallet_id": wallet.id,
                "amount": str(amount),
                "refund_reference": refund_transaction.internal_reference,
                "source_reference": (
                    source_transaction.internal_reference
                    if source_transaction
                    else None
                ),
            },
        )

        return refund_transaction

    @staticmethod
    def refund_reservation(reservation, amount=None, reason=""):
        """Refund a reservation payment back to the payer's wallet."""

        source_transaction = getattr(reservation, "wallet_transaction", None)

        if source_transaction is None:
            raise RefundError("Reservation has no associated wallet transaction.")

        amount = amount if amount is not None else source_transaction.amount

        return RefundService._refund_core(
            wallet=source_transaction.wallet,
            amount=amount,
            description=f"Reservation #{reservation.id} refund. {reason}".strip(),
            source_transaction=source_transaction,
            metadata={"reservation_id": reservation.id, "reason": reason},
        )

    @staticmethod
    def refund_invoice(invoice, wallet=None, amount=None, reason=""):
        """Refund an invoice payment back to the payer's wallet."""

        source_transaction = (
            WalletTransaction.objects.filter(
                invoice=invoice,
                status=WalletTransaction.TransactionStatus.SUCCESS,
            )
            .order_by("-created_at")
            .first()
        )

        if source_transaction is None:
            raise RefundError("No successful wallet transaction found for invoice.")

        target_wallet = wallet or source_transaction.wallet
        amount = amount if amount is not None else source_transaction.amount

        return RefundService._refund_core(
            wallet=target_wallet,
            amount=amount,
            description=f"Invoice #{invoice.id} refund. {reason}".strip(),
            source_transaction=source_transaction,
            metadata={"invoice_id": invoice.id, "reason": reason},
        )

    @staticmethod
    def refund_manual(wallet, amount, reason, requested_by=None):
        """Staff-initiated refund not tied to a specific transaction."""

        if not reason:
            raise RefundError("A reason is required for manual refunds.")

        return RefundService._refund_core(
            wallet=wallet,
            amount=amount,
            description=f"Manual refund: {reason}",
            metadata={
                "reason": reason,
                "requested_by": getattr(requested_by, "id", None),
                "manual": True,
            },
        )

    @staticmethod
    def refund_automatic(source_transaction, reason="Automatic refund"):
        """
        System-initiated refund (e.g. a downstream service failed after
        payment succeeded). Always refunds the full original amount.
        """

        return RefundService._refund_core(
            wallet=source_transaction.wallet,
            amount=source_transaction.amount,
            description=reason,
            source_transaction=source_transaction,
            metadata={"automatic": True, "reason": reason},
        )
