from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from wallets.models import TransactionType, Wallet, WalletTransaction, WalletType
from wallets.services import WalletService
from wallets.utils.reference import generate_internal_reference

from .factories import make_resident_wallet, make_system_wallet


class WalletModelTests(TestCase):

    def test_balance_cannot_go_negative_at_db_level(self):

        wallet = make_resident_wallet(balance=Decimal("100"))

        wallet.balance = Decimal("-1")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                wallet.save(update_fields=["balance"])

    def test_resident_wallet_requires_user(self):

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Wallet.objects.create(wallet_type=WalletType.RESIDENT, user=None)

    def test_system_wallet_str(self):

        wallet = make_system_wallet()

        self.assertEqual(str(wallet), "VillaHub")


class WalletTransactionStatusMachineTests(TestCase):

    def setUp(self):

        self.wallet = make_resident_wallet(balance=Decimal("0"))

    def _pending_transaction(self):

        return WalletService.create_pending_transaction(
            wallet=self.wallet,
            amount=Decimal("1000"),
            transaction_type=TransactionType.DEPOSIT,
        )

    def test_pending_to_success_is_allowed(self):

        wallet_transaction = self._pending_transaction()

        settled = WalletService.settle_pending_transaction(wallet_transaction)

        self.assertEqual(settled.status, WalletTransaction.TransactionStatus.SUCCESS)
        self.assertIsNotNone(settled.paid_at)
        self.assertIsNotNone(settled.verified_at)

    def test_success_to_pending_is_rejected(self):

        wallet_transaction = self._pending_transaction()
        WalletService.settle_pending_transaction(wallet_transaction)

        wallet_transaction.refresh_from_db()
        wallet_transaction.status = WalletTransaction.TransactionStatus.PENDING

        with self.assertRaises(ValidationError):
            wallet_transaction.full_clean()

    def test_failed_requires_failed_at_constraint(self):

        wallet_transaction = self._pending_transaction()
        wallet_transaction.status = WalletTransaction.TransactionStatus.FAILED
        wallet_transaction.failed_at = None

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                wallet_transaction.save()

    def test_internal_reference_is_unique(self):

        first = self._pending_transaction()
        second = self._pending_transaction()

        self.assertNotEqual(first.internal_reference, second.internal_reference)
        self.assertTrue(first.internal_reference.startswith("VH-TRX-"))
