import logging

from django.db import transaction

from ..models import Settlement, SettlementStatus
from ..utils.reference import generate_internal_reference

logger = logging.getLogger("wallets.services")


class SettlementError(Exception):
    pass


class SettlementService:

    @staticmethod
    @transaction.atomic
    def request(wallet, amount):

        return Settlement.objects.create(wallet=wallet, amount=amount)

    @staticmethod
    @transaction.atomic
    def approve(settlement):

        locked = Settlement.objects.select_for_update().get(pk=settlement.pk)

        if locked.status != SettlementStatus.PENDING:
            raise SettlementError("Only pending settlements can be approved.")

        locked.status = SettlementStatus.APPROVED
        locked.save(update_fields=["status", "updated_at"])

        return locked

    @staticmethod
    @transaction.atomic
    def pay(settlement, tracking_code):
        """
        Marks a settlement paid and books a WITHDRAW transaction against
        the township/system wallet for the settled amount, atomically.
        """

        from ..models import TransactionType, Wallet, WalletTransaction
        from .wallet_service import InsufficientBalanceError

        locked = Settlement.objects.select_for_update().get(pk=settlement.pk)

        if locked.status != SettlementStatus.APPROVED:
            raise SettlementError("Only approved settlements can be paid.")

        wallet = Wallet.objects.select_for_update().get(pk=locked.wallet_id)

        if wallet.balance < locked.amount:
            raise InsufficientBalanceError(
                f"Wallet {wallet.id} has insufficient balance to settle."
            )

        before = wallet.balance
        after = before - locked.amount
        wallet.balance = after
        wallet.save(update_fields=["balance", "updated_at"])

        from django.utils import timezone

        now = timezone.now()

        wallet_transaction = WalletTransaction(
            wallet=wallet,
            transaction_type=TransactionType.SETTLEMENT,
            amount=locked.amount,
            balance_before=before,
            balance_after=after,
            description=f"Settlement #{locked.id} payout",
            status=WalletTransaction.TransactionStatus.SUCCESS,
            paid_at=now,
            verified_at=now,
            reference=tracking_code,
        )
        wallet_transaction.internal_reference = generate_internal_reference(
            WalletTransaction,
        )
        wallet_transaction.full_clean()
        wallet_transaction.save()

        locked.status = SettlementStatus.PAID
        locked.tracking_code = tracking_code
        locked.paid_at = now
        locked.save(update_fields=["status", "tracking_code", "paid_at", "updated_at"])

        logger.info(
            "settlement.paid",
            extra={"settlement_id": locked.id, "amount": str(locked.amount)},
        )

        return locked
