from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from wallets.models import GatewayTransaction, TransactionType, WalletTransaction
from wallets.services import WalletService

from .factories import make_gateway, make_resident_wallet


class FakeAdapter:

    def __init__(self, verify_result):
        self._verify_result = verify_result

    def verify_payment(self, **kwargs):
        return self._verify_result


class PaymentCallbackViewTests(TestCase):
    """
    Exercises the single, idempotent HTTP entry point for gateway
    redirects (``PaymentCallbackView`` / name "wallet-payment-callback").
    """

    def setUp(self):

        self.client = APIClient()
        self.url = reverse("wallet-payment-callback")

        self.wallet = make_resident_wallet(balance=Decimal("0"))
        self.gateway = make_gateway()

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
            authority="A-CB-1",
        )
        self.wallet_transaction.authority = "A-CB-1"
        self.wallet_transaction.gateway = self.gateway
        self.wallet_transaction.save()

    def test_missing_authority_returns_400(self):

        response = self.client.get(self.url, {"Status": "OK"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_authority_returns_404(self):

        response = self.client.get(self.url, {"Authority": "does-not-exist", "Status": "OK"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_cancelled_payment(self):

        response = self.client.get(self.url, {"Authority": "A-CB-1", "Status": "NOK"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["success"])

        self.wallet_transaction.refresh_from_db()
        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet_transaction.status, WalletTransaction.TransactionStatus.CANCELLED,
        )
        self.assertEqual(self.wallet.balance, Decimal("0"))

    @mock.patch("wallets.services.payment_service.GatewayFactory")
    def test_successful_payment_credits_wallet(self, factory_mock):

        factory_mock.get.return_value = FakeAdapter(
            {"data": {"code": 100, "ref_id": "REF-CB-1"}},
        )

        response = self.client.get(self.url, {"Authority": "A-CB-1", "Status": "OK"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["reference"], "REF-CB-1")

        self.wallet.refresh_from_db()
        self.wallet_transaction.refresh_from_db()

        self.assertEqual(self.wallet.balance, Decimal("1000"))
        self.assertEqual(
            self.wallet_transaction.status, WalletTransaction.TransactionStatus.SUCCESS,
        )

    @mock.patch("wallets.services.payment_service.GatewayFactory")
    def test_duplicate_callback_does_not_double_credit(self, factory_mock):

        factory_mock.get.return_value = FakeAdapter(
            {"data": {"code": 100, "ref_id": "REF-CB-1"}},
        )

        first = self.client.get(self.url, {"Authority": "A-CB-1", "Status": "OK"})
        second = self.client.get(self.url, {"Authority": "A-CB-1", "Status": "OK"})

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)

        self.wallet.refresh_from_db()

        self.assertEqual(self.wallet.balance, Decimal("1000"))
        self.assertEqual(
            WalletTransaction.objects.filter(wallet=self.wallet).count(), 1,
        )

    @mock.patch("wallets.services.payment_service.GatewayFactory")
    def test_invalid_authority_at_gateway_marks_transaction_failed(self, factory_mock):

        factory_mock.get.return_value = FakeAdapter({"data": {"code": -11}})

        response = self.client.get(self.url, {"Authority": "A-CB-1", "Status": "OK"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["success"])

        self.wallet_transaction.refresh_from_db()
        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet_transaction.status, WalletTransaction.TransactionStatus.FAILED,
        )
        self.assertEqual(self.wallet.balance, Decimal("0"))
