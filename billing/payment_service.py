from django.db import transaction

from billing.models import (
    Invoice,
    InvoiceStatus,
)

from wallets.services import WalletService


class InvoicePaymentService:

    @staticmethod
    @transaction.atomic
    def pay_from_wallet(
        invoice,
        wallet,
    ):

        if invoice.remaining_amount <= 0:
            return invoice

        WalletService.withdraw(
            wallet=wallet,
            amount=invoice.remaining_amount,
            description=f"Invoice {invoice.invoice_number}",
            reference=invoice.invoice_number,
        )

        invoice.paid_amount += invoice.remaining_amount

        invoice.remaining_amount = 0

        invoice.status = InvoiceStatus.PAID

        invoice.save()

        return invoice