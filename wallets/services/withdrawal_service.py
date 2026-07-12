import logging

from django.db import transaction
from django.utils import timezone

from ..models import TransactionType, Wallet, WalletType, WithdrawalRequest
from .wallet_service import InsufficientBalanceError, InvalidAmountError, WalletService, _to_decimal

logger = logging.getLogger("wallets.services")


class WithdrawalError(Exception):
    pass


class WithdrawalService:

    @staticmethod
    @transaction.atomic
    def create_request(user, amount, bank_name="", account_owner="", card_number="",
                        sheba_number="", description=""):

        wallet = (
            Wallet.objects.select_for_update()
            .get(user=user, wallet_type=WalletType.RESIDENT, is_active=True)
        )

        amount = _to_decimal(amount)

        if amount > wallet.balance:
            raise InsufficientBalanceError("Insufficient balance.")

        return WithdrawalRequest.objects.create(
            wallet=wallet,
            amount=amount,
            status=WithdrawalRequest.Status.PENDING,
            bank_name=bank_name,
            account_owner=account_owner,
            card_number=card_number,
            sheba_number=sheba_number,
            description=description,
        )

    @staticmethod
    @transaction.atomic
    def approve(withdrawal_request, approved_by):

        locked = WithdrawalRequest.objects.select_for_update().get(
            pk=withdrawal_request.pk,
        )

        if locked.status != WithdrawalRequest.Status.PENDING:
            raise WithdrawalError("Only pending requests can be approved.")

        locked.status = WithdrawalRequest.Status.APPROVED
        locked.approved_by = approved_by
        locked.approved_at = timezone.now()
        locked.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

        return locked

    @staticmethod
    @transaction.atomic
    def pay(withdrawal_request, paid_by, tracking_code=""):

        locked = WithdrawalRequest.objects.select_for_update().get(
            pk=withdrawal_request.pk,
        )

        if locked.status != WithdrawalRequest.Status.APPROVED:
            raise WithdrawalError("Request must be approved before it can be paid.")

        wallet_transaction = WalletService.withdraw(
            wallet=locked.wallet,
            amount=locked.amount,
            description=f"Withdrawal request #{locked.id}",
            transaction_type=TransactionType.WITHDRAW,
        )

        locked.wallet_transaction = wallet_transaction
        locked.status = WithdrawalRequest.Status.PAID
        locked.tracking_code = tracking_code
        locked.paid_by = paid_by
        locked.paid_at = timezone.now()
        locked.save(
            update_fields=[
                "wallet_transaction",
                "status",
                "tracking_code",
                "paid_by",
                "paid_at",
                "updated_at",
            ]
        )

        logger.info(
            "withdrawal.paid",
            extra={"withdrawal_request_id": locked.id, "amount": str(locked.amount)},
        )

        return locked, wallet_transaction

    @staticmethod
    @transaction.atomic
    def reject(withdrawal_request, reason=""):

        locked = WithdrawalRequest.objects.select_for_update().get(
            pk=withdrawal_request.pk,
        )

        if locked.status != WithdrawalRequest.Status.PENDING:
            raise WithdrawalError("Only pending requests can be rejected.")

        locked.status = WithdrawalRequest.Status.REJECTED
        locked.reject_reason = reason
        locked.save(update_fields=["status", "reject_reason", "updated_at"])

        return locked
