import logging
from decimal import Decimal

from django.db import transaction

from ..models import CommissionRule, CommissionTransaction

logger = logging.getLogger("wallets.services")


class CommissionService:

    @staticmethod
    def calculate(township, amount):

        rule = CommissionRule.objects.get(township=township, is_active=True)

        return (Decimal(str(amount)) * rule.transaction_percent) / Decimal("100")

    @staticmethod
    @transaction.atomic
    def register(wallet_transaction, township, amount):

        rule = CommissionRule.objects.select_for_update().get(township=township)

        commission = CommissionTransaction.objects.create(
            wallet_transaction=wallet_transaction,
            township=township,
            amount=amount,
            percent=rule.transaction_percent,
        )

        logger.info(
            "commission.registered",
            extra={
                "township_id": township.id,
                "amount": str(amount),
                "wallet_transaction": wallet_transaction.internal_reference,
            },
        )

        return commission
