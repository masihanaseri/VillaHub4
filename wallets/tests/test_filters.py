from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from wallets.filters import (
    GatewayTransactionFilter,
    WalletTransactionFilter,
    WithdrawalRequestFilter,
)
from wallets.models import (
    GatewayTransaction,
    TransactionType,
    WalletTransaction,
    WithdrawalRequest,
)
from wallets.services import WalletService
from wallets.services.withdrawal_service import WithdrawalService

from .factories import make_gateway, make_resident_wallet, make_user


class WalletTransactionFilterTests(TestCase):

    def setUp(self):

        self.wallet = make_resident_wallet(balance=Decimal("0"))
        self.deposit = WalletService.deposit(self.wallet, Decimal("100"))
        self.withdrawal = WalletService.withdraw(self.wallet, Decimal("30"))

    def test_filters_by_transaction_type(self):

        qs = WalletTransactionFilter(
            {"transaction_type": TransactionType.DEPOSIT},
            queryset=WalletTransaction.objects.filter(wallet=self.wallet),
        ).qs

        self.assertEqual(list(qs), [self.deposit])

    def test_filters_by_status(self):

        qs = WalletTransactionFilter(
            {"status": WalletTransaction.TransactionStatus.SUCCESS},
            queryset=WalletTransaction.objects.filter(wallet=self.wallet),
        ).qs

        self.assertEqual(qs.count(), 2)

    def test_filters_by_min_and_max_amount(self):

        qs = WalletTransactionFilter(
            {"min_amount": "50", "max_amount": "200"},
            queryset=WalletTransaction.objects.filter(wallet=self.wallet),
        ).qs

        self.assertEqual(list(qs), [self.deposit])

    def test_filters_by_created_after_and_before(self):

        future = timezone.now() + timedelta(days=1)

        qs = WalletTransactionFilter(
            {"created_after": future.isoformat()},
            queryset=WalletTransaction.objects.filter(wallet=self.wallet),
        ).qs

        self.assertEqual(qs.count(), 0)

        past = timezone.now() - timedelta(days=1)

        qs = WalletTransactionFilter(
            {"created_after": past.isoformat()},
            queryset=WalletTransaction.objects.filter(wallet=self.wallet),
        ).qs

        self.assertEqual(qs.count(), 2)

    def test_filters_by_wallet(self):

        other_wallet = make_resident_wallet(balance=Decimal("0"))
        WalletService.deposit(other_wallet, Decimal("500"))

        qs = WalletTransactionFilter(
            {"wallet": self.wallet.pk},
            queryset=WalletTransaction.objects.all(),
        ).qs

        self.assertEqual(qs.count(), 2)
        self.assertTrue(all(t.wallet_id == self.wallet.pk for t in qs))


class GatewayTransactionFilterTests(TestCase):

    def setUp(self):

        self.wallet = make_resident_wallet(balance=Decimal("0"))
        self.gateway = make_gateway()

        self.verified_success = GatewayTransaction.objects.create(
            wallet=self.wallet, gateway=self.gateway, amount=Decimal("100"),
            authority="A-1", is_verified=True, is_success=True,
        )
        self.verified_failed = GatewayTransaction.objects.create(
            wallet=self.wallet, gateway=self.gateway, amount=Decimal("50"),
            authority="A-2", is_verified=True, is_success=False,
        )
        self.unverified = GatewayTransaction.objects.create(
            wallet=self.wallet, gateway=self.gateway, amount=Decimal("75"),
            authority="A-3", is_verified=False, is_success=False,
        )

    def test_filters_by_is_verified(self):

        qs = GatewayTransactionFilter(
            {"is_verified": "true"},
            queryset=GatewayTransaction.objects.filter(wallet=self.wallet),
        ).qs

        self.assertEqual(qs.count(), 2)

    def test_filters_by_is_success(self):

        qs = GatewayTransactionFilter(
            {"is_success": "true"},
            queryset=GatewayTransaction.objects.filter(wallet=self.wallet),
        ).qs

        self.assertEqual(list(qs), [self.verified_success])

    def test_filters_by_gateway(self):

        other_gateway = make_gateway(slug="other-gateway")
        GatewayTransaction.objects.create(
            wallet=self.wallet, gateway=other_gateway, amount=Decimal("10"), authority="A-4",
        )

        qs = GatewayTransactionFilter(
            {"gateway": self.gateway.pk},
            queryset=GatewayTransaction.objects.filter(wallet=self.wallet),
        ).qs

        self.assertEqual(qs.count(), 3)


class WithdrawalRequestFilterTests(TestCase):

    def setUp(self):

        self.user = make_user("withdrawal-filter-user")
        self.wallet = make_resident_wallet(user=self.user, balance=Decimal("10000"))

        self.pending = WithdrawalService.create_request(self.user, amount=Decimal("1000"))
        self.approved = WithdrawalService.create_request(self.user, amount=Decimal("2000"))
        WithdrawalService.approve(
            self.approved, approved_by=make_user("approver", is_staff=True),
        )
        self.approved.refresh_from_db()

    def test_filters_by_status(self):

        qs = WithdrawalRequestFilter(
            {"status": WithdrawalRequest.Status.PENDING},
            queryset=WithdrawalRequest.objects.filter(wallet=self.wallet),
        ).qs

        self.assertEqual(list(qs), [self.pending])

    def test_filters_by_wallet(self):

        other_user = make_user("other-withdrawal-user")
        other_wallet = make_resident_wallet(user=other_user, balance=Decimal("10000"))
        WithdrawalService.create_request(other_user, amount=Decimal("500"))

        qs = WithdrawalRequestFilter(
            {"wallet": self.wallet.pk},
            queryset=WithdrawalRequest.objects.all(),
        ).qs

        self.assertEqual(qs.count(), 2)
        self.assertTrue(all(w.wallet_id == self.wallet.pk for w in qs))

    def test_filters_by_created_after(self):

        future = timezone.now() + timedelta(days=1)

        qs = WithdrawalRequestFilter(
            {"created_after": future.isoformat()},
            queryset=WithdrawalRequest.objects.filter(wallet=self.wallet),
        ).qs

        self.assertEqual(qs.count(), 0)

    def test_ordering_by_amount(self):

        qs = WithdrawalRequest.objects.filter(wallet=self.wallet).order_by("amount")

        self.assertEqual(list(qs), [self.pending, self.approved])
