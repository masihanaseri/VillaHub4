"""
``WalletService`` is the *only* place in the codebase allowed to
mutate ``Wallet.balance``. Every public method:

* runs inside ``transaction.atomic()``
* takes a row lock with ``select_for_update()`` before reading the
  current balance, so concurrent deposits/withdrawals on the same
  wallet serialize instead of racing
* creates a ``WalletTransaction`` audit row recording balance_before /
  balance_after for every change, with a system-generated
  ``internal_reference``
* never trusts a client-supplied balance; the new balance is always
  ``balance_before ± amount`` computed here on the server
"""

import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from ..models import TransactionType, Wallet, WalletTransaction
from ..utils.reference import generate_internal_reference

logger = logging.getLogger("wallets.services")


class InsufficientBalanceError(Exception):
    """Raised when a withdrawal/transfer would take a wallet negative."""


class InvalidAmountError(Exception):
    """Raised for zero, negative, or unparsable amounts."""


def _to_decimal(amount):

    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise InvalidAmountError(f"Invalid amount: {amount!r}") from exc

    if amount <= 0:
        raise InvalidAmountError("Amount must be greater than zero.")

    return amount


class WalletService:

    @staticmethod
    @transaction.atomic
    def deposit(
        wallet,
        amount,
        description="",
        reference="",
        transaction_type=TransactionType.DEPOSIT,
        metadata=None,
    ):
        """
        Instantly credit ``wallet`` and record a SUCCESS transaction.

        Use this for operations that are complete the moment they're
        called (manual admin credit, commission, settlement, refund
        payout). Online gateway deposits go through
        ``PaymentGatewayService`` / ``PaymentService`` instead, since
        those need a PENDING row created *before* redirecting the user.
        """

        amount = _to_decimal(amount)

        locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        before = locked_wallet.balance
        after = before + amount

        locked_wallet.balance = after
        locked_wallet.save(update_fields=["balance", "updated_at"])

        now = timezone.now()

        wallet_transaction = WalletTransaction(
            wallet=locked_wallet,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=before,
            balance_after=after,
            description=description,
            reference=reference,
            status=WalletTransaction.TransactionStatus.SUCCESS,
            paid_at=now,
            verified_at=now,
            metadata=metadata or {},
        )
        wallet_transaction.internal_reference = generate_internal_reference(
            WalletTransaction,
        )
        wallet_transaction.full_clean()
        wallet_transaction.save()

        logger.info(
            "wallet.deposit",
            extra={
                "wallet_id": locked_wallet.id,
                "amount": str(amount),
                "internal_reference": wallet_transaction.internal_reference,
            },
        )

        wallet.balance = after
        return wallet_transaction

    @staticmethod
    @transaction.atomic
    def withdraw(
        wallet,
        amount,
        description="",
        reference="",
        transaction_type=TransactionType.WITHDRAW,
        metadata=None,
    ):
        """Instantly debit ``wallet``. Raises InsufficientBalanceError."""

        amount = _to_decimal(amount)

        locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        before = locked_wallet.balance

        if before < amount:
            raise InsufficientBalanceError(
                f"Wallet {locked_wallet.id} has insufficient balance: "
                f"balance={before}, requested={amount}."
            )

        after = before - amount

        locked_wallet.balance = after
        locked_wallet.save(update_fields=["balance", "updated_at"])

        now = timezone.now()

        wallet_transaction = WalletTransaction(
            wallet=locked_wallet,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=before,
            balance_after=after,
            description=description,
            reference=reference,
            status=WalletTransaction.TransactionStatus.SUCCESS,
            paid_at=now,
            verified_at=now,
            metadata=metadata or {},
        )
        wallet_transaction.internal_reference = generate_internal_reference(
            WalletTransaction,
        )
        wallet_transaction.full_clean()
        wallet_transaction.save()

        logger.info(
            "wallet.withdraw",
            extra={
                "wallet_id": locked_wallet.id,
                "amount": str(amount),
                "internal_reference": wallet_transaction.internal_reference,
            },
        )

        wallet.balance = after
        return wallet_transaction

    @staticmethod
    @transaction.atomic
    def create_pending_transaction(
        wallet,
        amount,
        transaction_type=TransactionType.DEPOSIT,
        description="",
        invoice=None,
        gateway=None,
        metadata=None,
    ):
        """
        Create a PENDING transaction *without* touching the balance.

        Used to open an online-payment flow: the row is created first,
        the user is redirected to the gateway, and the same row is
        later transitioned to SUCCESS/FAILED/EXPIRED by
        ``PaymentGatewayService`` — never duplicated.
        """

        amount = _to_decimal(amount)

        wallet_transaction = WalletTransaction(
            wallet=wallet,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=wallet.balance,
            balance_after=wallet.balance,
            description=description,
            invoice=invoice,
            gateway=gateway,
            status=WalletTransaction.TransactionStatus.PENDING,
            metadata=metadata or {},
        )
        wallet_transaction.internal_reference = generate_internal_reference(
            WalletTransaction,
        )
        wallet_transaction.full_clean()
        wallet_transaction.save()

        return wallet_transaction

    @staticmethod
    @transaction.atomic
    def settle_pending_transaction(wallet_transaction):
        """
        Idempotently transition a PENDING transaction to SUCCESS and
        apply its effect to the wallet balance.

        Safe to call multiple times (e.g. duplicate gateway callbacks):
        if the transaction is already SUCCESS, it's returned unchanged
        with no further balance mutation.
        """

        locked_transaction = (
            WalletTransaction.objects.select_for_update().get(
                pk=wallet_transaction.pk,
            )
        )

        if locked_transaction.status == WalletTransaction.TransactionStatus.SUCCESS:
            return locked_transaction

        if not locked_transaction.can_transition_to(
            WalletTransaction.TransactionStatus.SUCCESS,
        ):
            raise ValueError(
                f"Transaction {locked_transaction.internal_reference} cannot "
                f"transition from {locked_transaction.status} to SUCCESS."
            )

        locked_wallet = Wallet.objects.select_for_update().get(
            pk=locked_transaction.wallet_id,
        )

        before = locked_wallet.balance
        is_debit = locked_transaction.transaction_type in (
            TransactionType.WITHDRAW,
            TransactionType.TRANSFER_OUT,
        )
        after = before - locked_transaction.amount if is_debit else before + locked_transaction.amount

        if after < 0:
            raise InsufficientBalanceError(
                f"Settling transaction {locked_transaction.internal_reference} "
                f"would take wallet {locked_wallet.id} negative."
            )

        locked_wallet.balance = after
        locked_wallet.save(update_fields=["balance", "updated_at"])

        now = timezone.now()

        locked_transaction.balance_before = before
        locked_transaction.balance_after = after
        locked_transaction.status = WalletTransaction.TransactionStatus.SUCCESS
        locked_transaction.paid_at = locked_transaction.paid_at or now
        locked_transaction.verified_at = now
        locked_transaction.full_clean()
        locked_transaction.save()

        logger.info(
            "wallet.transaction.settled",
            extra={
                "wallet_id": locked_wallet.id,
                "internal_reference": locked_transaction.internal_reference,
            },
        )

        return locked_transaction

    @staticmethod
    @transaction.atomic
    def fail_pending_transaction(wallet_transaction, reason="", new_status=None):
        """Idempotently mark a PENDING transaction as FAILED/CANCELLED/EXPIRED."""

        from ..models import WalletTransaction as WT

        new_status = new_status or WT.TransactionStatus.FAILED

        locked_transaction = WT.objects.select_for_update().get(
            pk=wallet_transaction.pk,
        )

        if locked_transaction.status in WT.TERMINAL_STATUSES:
            return locked_transaction

        if not locked_transaction.can_transition_to(new_status):
            raise ValueError(
                f"Transaction {locked_transaction.internal_reference} cannot "
                f"transition from {locked_transaction.status} to {new_status}."
            )

        locked_transaction.status = new_status
        locked_transaction.failure_reason = reason
        if new_status == WT.TransactionStatus.FAILED:
            locked_transaction.failed_at = timezone.now()

        locked_transaction.full_clean()
        locked_transaction.save()

        logger.info(
            "wallet.transaction.failed",
            extra={
                "internal_reference": locked_transaction.internal_reference,
                "new_status": new_status,
                "reason": reason,
            },
        )

        return locked_transaction
