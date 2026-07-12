from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from wallets.models import WalletTransaction
from wallets.services import CleanupService, WalletService

from .factories import make_resident_wallet


class CleanupServiceTests(TestCase):

    @override_settings(WALLET_PENDING_TRANSACTION_TIMEOUT_MINUTES=30)
    def test_stale_pending_transaction_expires(self):

        wallet = make_resident_wallet(balance=Decimal("0"))

        stale = WalletService.create_pending_transaction(wallet=wallet, amount=Decimal("100"))
        WalletTransaction.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - timedelta(minutes=45),
        )

        fresh = WalletService.create_pending_transaction(wallet=wallet, amount=Decimal("100"))

        expired_count = CleanupService.expire_stale_pending_transactions()

        stale.refresh_from_db()
        fresh.refresh_from_db()

        self.assertEqual(expired_count, 1)
        self.assertEqual(stale.status, WalletTransaction.TransactionStatus.EXPIRED)
        self.assertEqual(fresh.status, WalletTransaction.TransactionStatus.PENDING)

    def test_expired_transactions_are_not_deleted(self):

        wallet = make_resident_wallet(balance=Decimal("0"))
        stale = WalletService.create_pending_transaction(wallet=wallet, amount=Decimal("100"))
        WalletTransaction.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - timedelta(hours=2),
        )

        CleanupService.expire_stale_pending_transactions()

        self.assertTrue(WalletTransaction.objects.filter(pk=stale.pk).exists())
