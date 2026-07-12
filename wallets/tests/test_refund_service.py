from decimal import Decimal

from django.test import TestCase

from wallets.models import TransactionType, WalletTransaction
from wallets.services import RefundService, WalletService
from wallets.services.refund_service import RefundError

from .factories import make_resident_wallet


class RefundServiceTests(TestCase):

    def setUp(self):

        self.wallet = make_resident_wallet(balance=Decimal("0"))

    def _make_success_transaction(self, amount=Decimal("1000")):

        pending = WalletService.create_pending_transaction(
            wallet=self.wallet, amount=amount, transaction_type=TransactionType.PAYMENT,
        )
        return WalletService.settle_pending_transaction(pending)

    def test_refund_manual_credits_wallet(self):

        RefundService.refund_manual(self.wallet, Decimal("100"), reason="Goodwill credit")

        self.wallet.refresh_from_db()

        self.assertEqual(self.wallet.balance, Decimal("100"))

    def test_refund_manual_without_reason_rejected(self):

        with self.assertRaises(RefundError):
            RefundService.refund_manual(self.wallet, Decimal("100"), reason="")

    def test_refund_automatic_marks_source_refunded_and_credits_wallet(self):

        source = self._make_success_transaction(Decimal("1000"))

        RefundService.refund_automatic(source)

        source.refresh_from_db()
        self.wallet.refresh_from_db()

        self.assertEqual(source.status, WalletTransaction.TransactionStatus.REFUNDED)
        self.assertEqual(self.wallet.balance, Decimal("1000"))

    def test_double_refund_rejected(self):

        source = self._make_success_transaction(Decimal("1000"))

        RefundService.refund_automatic(source)
        source.refresh_from_db()

        with self.assertRaises(RefundError):
            RefundService.refund_automatic(source)

    def test_cannot_refund_pending_transaction(self):

        pending = WalletService.create_pending_transaction(
            wallet=self.wallet, amount=Decimal("500"),
        )

        with self.assertRaises(RefundError):
            RefundService.refund_automatic(pending)
