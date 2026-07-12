from decimal import Decimal

from django.core.exceptions import ValidationError


def validate_positive_amount(value):

    if value is None or value <= Decimal("0"):
        raise ValidationError("Amount must be greater than zero.")


MIN_TRANSFER_AMOUNT = Decimal("1000")
MIN_WITHDRAWAL_AMOUNT = Decimal("50000")


def validate_withdrawal_amount(value):

    validate_positive_amount(value)

    if value < MIN_WITHDRAWAL_AMOUNT:
        raise ValidationError(
            f"Withdrawal amount must be at least {MIN_WITHDRAWAL_AMOUNT}."
        )
