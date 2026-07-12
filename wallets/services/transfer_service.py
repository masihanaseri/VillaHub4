"""
Transfers move funds between two wallets as a single atomic unit: if
either leg fails, the whole transfer rolls back and neither
``WalletTransaction`` row is left behind (Django wraps the failing
statement in ``transaction.atomic()`` and rolls back on exception).

Both wallet rows are locked in a fixed order (ascending primary key)
before any balance is read, regardless of which wallet is the sender.
This avoids the classic "A locks 1-then-2 while B locks 2-then-1"
deadlock that a naive select_for_update on wallet-then-destination
would otherwise create if two transfers run in opposite directions
concurrently.
"""

import logging

from django.db import transaction

from ..models import TransactionType, Wallet, WalletTransaction
from .wallet_service import InsufficientBalanceError, WalletService, _to_decimal

logger = logging.getLogger("wallets.services")


class TransferService:

    @staticmethod
    @transaction.atomic
    def transfer(source_wallet, destination_wallet, amount, description=""):

        if source_wallet.pk == destination_wallet.pk:
            raise ValueError("Cannot transfer a wallet to itself.")

        amount = _to_decimal(amount)

        # Lock both wallets in a stable order to prevent deadlocks.
        ordered_ids = sorted([source_wallet.pk, destination_wallet.pk])
        locked_wallets = {
            w.pk: w
            for w in Wallet.objects.select_for_update().filter(
                pk__in=ordered_ids,
            )
        }

        locked_source = locked_wallets[source_wallet.pk]
        locked_destination = locked_wallets[destination_wallet.pk]

        if locked_source.balance < amount:
            raise InsufficientBalanceError(
                f"Wallet {locked_source.id} has insufficient balance for transfer."
            )

        source_before = locked_source.balance
        source_after = source_before - amount

        destination_before = locked_destination.balance
        destination_after = destination_before + amount

        locked_source.balance = source_after
        locked_source.save(update_fields=["balance", "updated_at"])

        locked_destination.balance = destination_after
        locked_destination.save(update_fields=["balance", "updated_at"])

        from ..utils.reference import generate_internal_reference

        outgoing = WalletTransaction(
            wallet=locked_source,
            transaction_type=TransactionType.TRANSFER_OUT,
            amount=amount,
            balance_before=source_before,
            balance_after=source_after,
            description=description or f"Transfer to wallet {locked_destination.id}",
            status=WalletTransaction.TransactionStatus.SUCCESS,
        )
        outgoing.internal_reference = generate_internal_reference(WalletTransaction)

        incoming = WalletTransaction(
            wallet=locked_destination,
            transaction_type=TransactionType.TRANSFER_IN,
            amount=amount,
            balance_before=destination_before,
            balance_after=destination_after,
            description=description or f"Transfer from wallet {locked_source.id}",
            status=WalletTransaction.TransactionStatus.SUCCESS,
            reference=outgoing.internal_reference,
        )
        incoming.internal_reference = generate_internal_reference(WalletTransaction)
        outgoing.reference = incoming.internal_reference

        from django.utils import timezone

        now = timezone.now()
        outgoing.paid_at = outgoing.verified_at = now
        incoming.paid_at = incoming.verified_at = now

        outgoing.full_clean()
        outgoing.save()

        incoming.full_clean()
        incoming.save()

        logger.info(
            "wallet.transfer",
            extra={
                "source_wallet_id": locked_source.id,
                "destination_wallet_id": locked_destination.id,
                "amount": str(amount),
                "outgoing_reference": outgoing.internal_reference,
                "incoming_reference": incoming.internal_reference,
            },
        )

        source_wallet.balance = source_after
        destination_wallet.balance = destination_after

        return outgoing, incoming
