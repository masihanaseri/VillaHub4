from decimal import Decimal

from django.test import TestCase

from wallets.models import WithdrawalRequest
from wallets.services import InsufficientBalanceError
from wallets.services.withdrawal_service import WithdrawalError, WithdrawalService

from .factories import make_resident_wallet, make_user


class WithdrawalServiceTests(TestCase):

    def setUp(self):

        self.user = make_user("carol")
        self.wallet = make_resident_wallet(user=self.user, balance=Decimal("1000"))
        self.staff = make_user("staff", is_staff=True)

    def test_create_request_requires_sufficient_balance(self):

        with self.assertRaises(InsufficientBalanceError):
            WithdrawalService.create_request(self.user, amount=Decimal("2000"))

    def test_full_lifecycle_approve_then_pay_debits_wallet(self):

        request = WithdrawalService.create_request(self.user, amount=Decimal("300"))
        WithdrawalService.approve(request, approved_by=self.staff)

        request, wallet_transaction = WithdrawalService.pay(
            request, paid_by=self.staff, tracking_code="TRK-1",
        )

        self.wallet.refresh_from_db()

        self.assertEqual(request.status, WithdrawalRequest.Status.PAID)
        self.assertEqual(self.wallet.balance, Decimal("700"))
        self.assertEqual(wallet_transaction.amount, Decimal("300"))

    def test_cannot_pay_before_approval(self):

        request = WithdrawalService.create_request(self.user, amount=Decimal("300"))

        with self.assertRaises(WithdrawalError):
            WithdrawalService.pay(request, paid_by=self.staff)

    def test_reject_pending_request(self):

        request = WithdrawalService.create_request(self.user, amount=Decimal("300"))
        WithdrawalService.reject(request, reason="Suspicious account")

        request.refresh_from_db()

        self.assertEqual(request.status, WithdrawalRequest.Status.REJECTED)
        self.assertEqual(request.reject_reason, "Suspicious account")
