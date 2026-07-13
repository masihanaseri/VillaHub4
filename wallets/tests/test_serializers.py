from decimal import Decimal

from django.test import TestCase

from wallets.models import TransactionType, WalletTransaction
from wallets.serializers import (
    CommissionRuleSerializer,
    CommissionTransactionSerializer,
    DepositRequestSerializer,
    GatewayCallbackSerializer,
    GatewayTransactionSerializer,
    OnlineDepositRequestSerializer,
    PaymentGatewaySerializer,
    SettlementSerializer,
    TransferRequestSerializer,
    WalletSerializer,
    WalletTransactionSerializer,
    WithdrawalRequestCreateSerializer,
    WithdrawalRequestPaySerializer,
    WithdrawalRequestRejectSerializer,
    WithdrawalRequestSerializer,
    WithdrawRequestSerializer,
)
from wallets.services import WalletService

from .factories import (
    make_commission_rule,
    make_gateway,
    make_resident_wallet,
    make_township,
    make_township_wallet,
)


class WalletSerializerTests(TestCase):

    def test_balance_and_uuid_are_read_only(self):

        wallet = make_resident_wallet(balance=Decimal("500"))

        serializer = WalletSerializer(
            wallet, data={"balance": "999999", "uuid": "x" * 8, "is_active": False}, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        self.assertEqual(updated.balance, Decimal("500"))
        self.assertNotEqual(str(updated.uuid), "x" * 8)
        self.assertFalse(updated.is_active)

    def test_serializes_expected_fields(self):

        wallet = make_resident_wallet(balance=Decimal("500"))

        data = WalletSerializer(wallet).data

        self.assertEqual(Decimal(data["balance"]), Decimal("500"))
        self.assertIn("uuid", data)
        self.assertIn("wallet_type", data)


class WalletTransactionSerializerTests(TestCase):

    def test_ledger_fields_are_read_only(self):

        wallet = make_resident_wallet(balance=Decimal("0"))
        wallet_transaction = WalletService.deposit(wallet, Decimal("100"))

        serializer = WalletTransactionSerializer(
            wallet_transaction,
            data={
                "status": "REFUNDED",
                "balance_before": "0",
                "balance_after": "999",
                "internal_reference": "HACKED",
            },
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        self.assertEqual(updated.status, WalletTransaction.TransactionStatus.SUCCESS)
        self.assertEqual(updated.balance_after, Decimal("100"))
        self.assertNotEqual(updated.internal_reference, "HACKED")


class DepositRequestSerializerTests(TestCase):

    def test_valid_data(self):

        serializer = DepositRequestSerializer(data={"amount": "100.50", "description": "test"})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["amount"], Decimal("100.50"))

    def test_amount_is_required(self):

        serializer = DepositRequestSerializer(data={"description": "test"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)

    def test_zero_amount_rejected_by_min_value(self):

        serializer = DepositRequestSerializer(data={"amount": "0"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)

    def test_negative_amount_rejected(self):

        serializer = DepositRequestSerializer(data={"amount": "-5"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)

    def test_description_defaults_to_blank(self):

        serializer = DepositRequestSerializer(data={"amount": "10"})
        serializer.is_valid(raise_exception=True)

        self.assertEqual(serializer.validated_data["description"], "")

    def test_too_many_decimal_places_rejected(self):

        serializer = DepositRequestSerializer(data={"amount": "10.999"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)


class WithdrawRequestSerializerTests(TestCase):

    def test_valid_data(self):

        serializer = WithdrawRequestSerializer(data={"amount": "50"})

        self.assertTrue(serializer.is_valid())


class TransferRequestSerializerTests(TestCase):

    def test_valid_data_resolves_destination_wallet(self):

        destination = make_resident_wallet()

        serializer = TransferRequestSerializer(
            data={"destination_wallet": destination.pk, "amount": "10"},
        )
        serializer.is_valid(raise_exception=True)

        self.assertEqual(serializer.validated_data["destination_wallet"], destination)

    def test_unknown_destination_wallet_rejected(self):

        serializer = TransferRequestSerializer(
            data={"destination_wallet": 999999, "amount": "10"},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("destination_wallet", serializer.errors)

    def test_missing_amount_rejected(self):

        destination = make_resident_wallet()

        serializer = TransferRequestSerializer(data={"destination_wallet": destination.pk})

        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)


class OnlineDepositRequestSerializerTests(TestCase):

    def test_valid_data(self):

        serializer = OnlineDepositRequestSerializer(data={"amount": "1000"})

        self.assertTrue(serializer.is_valid())


class SettlementSerializerTests(TestCase):

    def test_status_and_tracking_code_are_read_only(self):

        from wallets.services.settlement_service import SettlementService

        wallet = make_township_wallet(balance=Decimal("1000"))
        settlement = SettlementService.request(wallet, Decimal("500"))

        serializer = SettlementSerializer(
            settlement, data={"status": "PAID", "tracking_code": "HACKED"}, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        self.assertEqual(updated.status, "PENDING")
        self.assertEqual(updated.tracking_code, "")


class CommissionRuleSerializerTests(TestCase):

    def test_valid_data(self):

        township = make_township()

        serializer = CommissionRuleSerializer(
            data={
                "township": township.pk,
                "monthly_subscription": "0",
                "transaction_percent": "3.5",
                "is_active": True,
            },
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_township_rejected(self):

        serializer = CommissionRuleSerializer(
            data={"monthly_subscription": "0", "transaction_percent": "3.5"},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("township", serializer.errors)


class CommissionTransactionSerializerTests(TestCase):

    def test_serializes_expected_fields(self):

        wallet = make_resident_wallet(balance=Decimal("0"))
        wallet_transaction = WalletService.deposit(wallet, Decimal("100"))
        rule = make_commission_rule()

        from wallets.models import CommissionTransaction

        commission = CommissionTransaction.objects.create(
            wallet_transaction=wallet_transaction,
            township=rule.township,
            amount=Decimal("2"),
            percent=rule.transaction_percent,
        )

        data = CommissionTransactionSerializer(commission).data

        self.assertEqual(Decimal(data["amount"]), Decimal("2"))
        self.assertIn("created_at", data)


class PaymentGatewaySerializerTests(TestCase):

    def test_secret_fields_are_write_only(self):

        gateway = make_gateway()

        data = PaymentGatewaySerializer(gateway).data

        self.assertNotIn("merchant_id", data)
        self.assertNotIn("sandbox_merchant_id", data)
        self.assertNotIn("production_merchant_id", data)
        self.assertNotIn("api_key", data)
        self.assertIn("slug", data)

    def test_can_write_secret_fields(self):

        serializer = PaymentGatewaySerializer(
            data={
                "name": "ZarinPal",
                "slug": "zarinpal-write-test",
                "merchant_id": "secret",
                "priority": 1,
            },
        )
        serializer.is_valid(raise_exception=True)
        gateway = serializer.save()

        self.assertEqual(gateway.merchant_id, "secret")


class GatewayTransactionSerializerTests(TestCase):

    def test_verification_fields_are_read_only(self):

        wallet = make_resident_wallet(balance=Decimal("0"))
        gateway = make_gateway()

        from wallets.models import GatewayTransaction

        gateway_transaction = GatewayTransaction.objects.create(
            wallet=wallet, gateway=gateway, amount=Decimal("100"), authority="A-X",
        )

        serializer = GatewayTransactionSerializer(
            gateway_transaction,
            data={"is_verified": True, "is_success": True, "ref_id": "HACKED"},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        self.assertFalse(updated.is_verified)
        self.assertFalse(updated.is_success)
        self.assertEqual(updated.ref_id, "")


class GatewayCallbackSerializerTests(TestCase):

    def test_serializer_can_be_instantiated_and_is_fully_read_only(self):
        """
        Regression test: `read_only_fields` used to reference the
        string "__all__" instead of an explicit tuple, which raised
        TypeError the moment DRF built the serializer's fields.
        """

        from wallets.models import GatewayCallback

        callback = GatewayCallback.objects.create(raw_data={"a": 1})

        serializer = GatewayCallbackSerializer(callback)

        # Must not raise, and every field must come back read-only.
        fields = serializer.fields
        self.assertTrue(fields)
        for field in fields.values():
            self.assertTrue(field.read_only)

    def test_write_attempt_is_ignored(self):

        from wallets.models import GatewayCallback

        callback = GatewayCallback.objects.create(raw_data={"a": 1})

        serializer = GatewayCallbackSerializer(
            callback, data={"processed": True}, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        self.assertFalse(updated.processed)


class WithdrawalRequestSerializerTests(TestCase):

    def test_administrative_and_amount_fields_are_read_only(self):
        """
        `amount` must stay read-only through this serializer: it is
        fixed at creation (validated against balance/minimum by
        WithdrawalService.create_request), and the owner of a
        still-PENDING request must not be able to bump it afterwards.
        """

        from wallets.services.withdrawal_service import WithdrawalService

        from .factories import make_user

        user = make_user("withdrawal-owner")
        make_resident_wallet(user=user, balance=Decimal("1000"))

        withdrawal_request = WithdrawalService.create_request(user, amount=Decimal("500"))

        serializer = WithdrawalRequestSerializer(
            withdrawal_request, data={"status": "PAID", "amount": "1"}, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        self.assertEqual(updated.status, "PENDING")
        self.assertEqual(updated.amount, Decimal("500"))


class WithdrawalRequestCreateSerializerTests(TestCase):

    def test_valid_minimal_data(self):

        serializer = WithdrawalRequestCreateSerializer(data={"amount": "50000"})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["bank_name"], "")

    def test_amount_required(self):

        serializer = WithdrawalRequestCreateSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)


class WithdrawalRequestPaySerializerTests(TestCase):

    def test_tracking_code_optional(self):

        serializer = WithdrawalRequestPaySerializer(data={})
        serializer.is_valid(raise_exception=True)

        self.assertEqual(serializer.validated_data["tracking_code"], "")


class WithdrawalRequestRejectSerializerTests(TestCase):

    def test_reason_optional(self):

        serializer = WithdrawalRequestRejectSerializer(data={})
        serializer.is_valid(raise_exception=True)

        self.assertEqual(serializer.validated_data["reason"], "")
