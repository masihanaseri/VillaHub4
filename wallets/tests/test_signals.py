from decimal import Decimal

from django.test import TestCase

from wallets.services import WalletService

from .factories import make_resident_wallet


class WalletTransactionSignalTests(TestCase):

    def setUp(self):

        self.wallet = make_resident_wallet(balance=Decimal("0"))

    def test_deposit_logs_structured_audit_entry(self):

        with self.assertLogs("wallets.audit", level="INFO") as captured:
            wallet_transaction = WalletService.deposit(self.wallet, Decimal("500"))

        self.assertTrue(
            any("wallet_transaction.saved" in message for message in captured.output)
        )
        record = captured.records[-1]
        self.assertEqual(record.internal_reference, wallet_transaction.internal_reference)
        self.assertTrue(record.was_created)
        self.assertEqual(record.amount, "500")

    def test_signal_fires_again_on_update_with_created_false(self):

        wallet_transaction = WalletService.deposit(self.wallet, Decimal("500"))

        with self.assertLogs("wallets.audit", level="INFO") as captured:
            wallet_transaction.description = "updated description"
            wallet_transaction.save(update_fields=["description"])

        record = captured.records[-1]
        self.assertFalse(record.was_created)
        self.assertEqual(record.internal_reference, wallet_transaction.internal_reference)

    def test_signal_is_side_effect_free_for_balance(self):
        """
        The audit signal must never itself mutate wallet balance —
        only the service layer that triggered the save may do that.
        """

        before = self.wallet.balance

        WalletService.deposit(self.wallet, Decimal("250"))

        self.wallet.refresh_from_db()

        self.assertEqual(self.wallet.balance, before + Decimal("250"))
