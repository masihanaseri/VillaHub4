from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from .models import (
    Wallet,
    WalletTransaction,
    TransactionType,
    Settlement,
    CommissionRule,
    CommissionTransaction,
)


class WalletService:

    @staticmethod
    @transaction.atomic
    def deposit(
        wallet,
        amount,
        description="",
        reference="",
    ):

        amount = Decimal(amount)

        before = wallet.balance

        wallet.balance += amount

        wallet.save()

        return WalletTransaction.objects.create(

            wallet=wallet,

            transaction_type=TransactionType.DEPOSIT,

            amount=amount,

            balance_before=before,

            balance_after=wallet.balance,

            description=description,

            reference=reference,

            status=WalletTransaction.TransactionStatus.SUCCESS,

        )

    @staticmethod
    @transaction.atomic
    def withdraw(
        wallet,
        amount,
        description="",
        reference="",
    ):

        amount = Decimal(amount)

        if wallet.balance < amount:

            raise Exception("Insufficient balance")

        before = wallet.balance

        wallet.balance -= amount

        wallet.save()

        return WalletTransaction.objects.create(

            wallet=wallet,

            transaction_type=TransactionType.WITHDRAW,

            amount=amount,

            balance_before=before,

            balance_after=wallet.balance,

            description=description,

            reference=reference,

            status=WalletTransaction.TransactionStatus.SUCCESS,
        )

    @staticmethod
    @transaction.atomic
    def transfer(
        source_wallet,
        destination_wallet,
        amount,
        description="",
    ):

        WalletService.withdraw(

            source_wallet,

            amount,

            description,

        )

        WalletService.deposit(

            destination_wallet,

            amount,

            description,

        )

        return True
    
    @staticmethod
    def create_deposit_transaction(
        wallet,
        amount,
        description="",
    ):

        amount = Decimal(amount)

        return WalletTransaction.objects.create(

            wallet=wallet,

            transaction_type=TransactionType.DEPOSIT,

            amount=amount,

            balance_before=wallet.balance,

            balance_after=wallet.balance,

            description=description,

            status=WalletTransaction.TransactionStatus.PENDING,

        )


    @staticmethod
    @transaction.atomic
    def confirm_deposit(
        wallet_transaction,
    ):

        if wallet_transaction.status == WalletTransaction.TransactionStatus.SUCCESS:
            return wallet_transaction

        wallet = wallet_transaction.wallet

        before = wallet.balance

        wallet.balance += wallet_transaction.amount

        wallet.save()

        wallet_transaction.balance_before = before

        wallet_transaction.balance_after = wallet.balance

        wallet_transaction.status = WalletTransaction.TransactionStatus.SUCCESS



        wallet_transaction.paid_at = timezone.now()
        wallet_transaction.verified_at = timezone.now()



        wallet_transaction.save()

        return wallet_transaction

class CommissionService:

    @staticmethod
    def calculate(

        township,

        amount,

    ):

        rule = CommissionRule.objects.get(

            township=township,

            is_active=True,

        )

        commission = (

            Decimal(amount)

            * rule.transaction_percent

            / Decimal("100")

        )

        return commission

    @staticmethod
    @transaction.atomic
    def register(

        wallet_transaction,

        township,

        amount,

    ):

        rule = CommissionRule.objects.get(

            township=township,

        )

        return CommissionTransaction.objects.create(

            wallet_transaction=wallet_transaction,

            township=township,

            amount=amount,

            percent=rule.transaction_percent,

        )
    
class SettlementService:

    @staticmethod
    def request(

        wallet,

        amount,

    ):

        return Settlement.objects.create(

            wallet=wallet,

            amount=amount,

        )

    @staticmethod
    def approve(

        settlement,

    ):

        settlement.status = "APPROVED"

        settlement.save()

        return settlement

    @staticmethod
    def pay(

        settlement,

        tracking_code,

    ):

        settlement.status = "PAID"

        settlement.tracking_code = tracking_code

        settlement.save()

        return settlement
    
