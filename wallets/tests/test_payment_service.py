from decimal import Decimal
from unittest import mock

from django.test import RequestFactory, TestCase

from wallets.models import (
    GatewayTransaction,
    PaymentGateway,
    TransactionType,
    WalletTransaction,
)
from wallets.services import PaymentGatewayService, WalletService

from .factories import make_resident_wallet


class FakeZarinPalAdapter:
    """Deterministic stand-in for the real HTTP-calling adapter."""

    def __init__(self, verify_result):
        self._verify_result = verify_result

    def create_payment(self, **kwargs):
        return {"data": {"authority": "A-000-TEST"}, "errors": []}

    def get_payment_url(self, authority, sandbox=False):
        return f"https://sandbox.zarinpal.com/pg/StartPay/{authority}"

    def verify_payment(self, **kwargs):
        return self._verify_result


class PaymentCallbackIdempotencyTests(TestCase):

    def setUp(self):

        self.wallet = make_resident_wallet(balance=Decimal("0"))
        self.gateway = PaymentGateway.objects.create(
            name="ZarinPal", slug="zarinpal", merchant_id="x",
            sandbox=True, is_active=True, priority=1,
        )
        self.wallet_transaction = WalletService.create_pending_transaction(
            wallet=self.wallet,
            amount=Decimal("1000"),
            transaction_type=TransactionType.DEPOSIT,
        )
        self.gateway_transaction = GatewayTransaction.objects.create(
            wallet=self.wallet,
            gateway=self.gateway,
            wallet_transaction=self.wallet_transaction,
            amount=Decimal("1000"),
            authority="A-000-TEST",
        )
        self.wallet_transaction.authority = "A-000-TEST"
        self.wallet_transaction.gateway = self.gateway
        self.wallet_transaction.save()

        self.factory = RequestFactory()

    def _get_request(self):

        return self.factory.get(
            "/wallet/payment/callback/",
            {"Authority": "A-000-TEST", "Status": "OK"},
        )

    @mock.patch("wallets.services.payment_service.GatewayFactory")
    def test_successful_callback_settles_transaction_once(self, factory_mock):

        factory_mock.get.return_value = FakeZarinPalAdapter(
            {"data": {"code": 100, "ref_id": "REF-1"}},
        )

        gt, wt = PaymentGatewayService.handle_callback(
            authority="A-000-TEST", gateway_status_param="OK", request=self._get_request(),
        )

        self.wallet.refresh_from_db()

        self.assertTrue(gt.is_success)
        self.assertEqual(wt.status, WalletTransaction.TransactionStatus.SUCCESS)
        self.assertEqual(self.wallet.balance, Decimal("1000"))

    @mock.patch("wallets.services.payment_service.GatewayFactory")
    def test_duplicate_callback_does_not_double_credit(self, factory_mock):

        adapter = FakeZarinPalAdapter({"data": {"code": 100, "ref_id": "REF-1"}})
        factory_mock.get.return_value = adapter

        PaymentGatewayService.handle_callback(
            authority="A-000-TEST", gateway_status_param="OK", request=self._get_request(),
        )
        # Simulate the gateway (or a malicious replay) hitting the
        # callback URL a second time for the same authority.
        PaymentGatewayService.handle_callback(
            authority="A-000-TEST", gateway_status_param="OK", request=self._get_request(),
        )

        self.wallet.refresh_from_db()

        self.assertEqual(self.wallet.balance, Decimal("1000"))
        self.assertEqual(
            WalletTransaction.objects.filter(wallet=self.wallet).count(), 1,
        )

    @mock.patch("wallets.services.payment_service.GatewayFactory")
    def test_failed_verification_marks_transaction_failed_not_success(self, factory_mock):

        factory_mock.get.return_value = FakeZarinPalAdapter(
            {"data": {"code": -1}},
        )

        gt, wt = PaymentGatewayService.handle_callback(
            authority="A-000-TEST", gateway_status_param="OK", request=self._get_request(),
        )

        self.wallet.refresh_from_db()

        self.assertFalse(gt.is_success)
        self.assertEqual(wt.status, WalletTransaction.TransactionStatus.FAILED)
        self.assertEqual(self.wallet.balance, Decimal("0"))

    def test_user_cancelled_marks_transaction_cancelled(self):

        request = self.factory.get(
            "/wallet/payment/callback/",
            {"Authority": "A-000-TEST", "Status": "NOK"},
        )

        gt, wt = PaymentGatewayService.handle_callback(
            authority="A-000-TEST", gateway_status_param="NOK", request=request,
        )

        self.wallet.refresh_from_db()

        self.assertFalse(gt.is_success)
        self.assertEqual(wt.status, WalletTransaction.TransactionStatus.CANCELLED)
        self.assertEqual(self.wallet.balance, Decimal("0"))
