"""
Paths match the router registrations in the project's ``urls.py``
(note the ``CommissionTransactionViewSet`` route is registered as
"commissions", not "commission-transactions").
"""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from wallets.models import CommissionTransaction
from wallets.services import WalletService
from wallets.services.settlement_service import SettlementService

from .factories import (
    make_commission_rule,
    make_resident_wallet,
    make_township,
    make_township_wallet,
    make_user,
)

SETTLEMENTS_URL = "/wallets/settlements/"
COMMISSION_RULES_URL = "/wallets/commission-rules/"
COMMISSION_TRANSACTIONS_URL = "/wallets/commissions/"


class SettlementViewSetTests(APITestCase):

    def setUp(self):

        self.owner = make_user("township-owner")
        self.township = make_township()
        self.wallet = make_township_wallet(
            township=self.township, user=None, balance=Decimal("5000"),
        )
        # A township wallet's "owner" for read access is whoever holds
        # a TOWNSHIP wallet for that township — see
        # CommissionTransactionViewSet.get_queryset for the same rule.
        self.wallet.user = self.owner
        self.wallet.save(update_fields=["user"])

        self.staff = make_user("settlement-staff", is_staff=True)
        self.other_user = make_user("settlement-outsider")

        self.settlement = SettlementService.request(self.wallet, Decimal("1000"))

    def test_owner_can_list_own_settlements(self):

        self.client.force_authenticate(self.owner)

        response = self.client.get(SETTLEMENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in (response.data["results"] if isinstance(response.data, dict) else response.data)}
        self.assertIn(self.settlement.id, returned_ids)

    def test_outsider_does_not_see_others_settlements(self):

        self.client.force_authenticate(self.other_user)

        response = self.client.get(SETTLEMENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in (response.data["results"] if isinstance(response.data, dict) else response.data)}
        self.assertNotIn(self.settlement.id, returned_ids)

    def test_owner_cannot_create_settlement_via_write_endpoint(self):
        """
        `ReadOnlyOrFinanceStaff` restricts every non-safe method
        (including create) to finance staff; regular owners can only
        read, never POST directly to the collection endpoint.
        """

        self.client.force_authenticate(self.owner)

        response = self.client.post(
            SETTLEMENTS_URL, {"wallet": self.wallet.pk, "amount": "100"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_staff_cannot_approve(self):

        self.client.force_authenticate(self.owner)

        response = self.client.post(f"{SETTLEMENTS_URL}{self.settlement.pk}/approve/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_approve_then_pay(self):

        self.client.force_authenticate(self.staff)

        approve_response = self.client.post(f"{SETTLEMENTS_URL}{self.settlement.pk}/approve/")
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data["status"], "APPROVED")

        pay_response = self.client.post(
            f"{SETTLEMENTS_URL}{self.settlement.pk}/pay/", {"tracking_code": "TRK-API-1"},
        )
        self.assertEqual(pay_response.status_code, status.HTTP_200_OK)
        self.assertEqual(pay_response.data["status"], "PAID")

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("4000"))

    def test_pay_before_approve_returns_400(self):

        self.client.force_authenticate(self.staff)

        response = self.client.post(
            f"{SETTLEMENTS_URL}{self.settlement.pk}/pay/", {"tracking_code": "TRK-X"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pay_with_insufficient_wallet_balance_returns_400(self):

        self.client.force_authenticate(self.staff)
        self.client.post(f"{SETTLEMENTS_URL}{self.settlement.pk}/approve/")

        self.wallet.balance = Decimal("10")
        self.wallet.save(update_fields=["balance"])

        response = self.client.post(
            f"{SETTLEMENTS_URL}{self.settlement.pk}/pay/", {"tracking_code": "TRK-X"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_pay_returns_400(self):

        self.client.force_authenticate(self.staff)
        self.client.post(f"{SETTLEMENTS_URL}{self.settlement.pk}/approve/")
        self.client.post(
            f"{SETTLEMENTS_URL}{self.settlement.pk}/pay/", {"tracking_code": "TRK-1"},
        )

        response = self.client.post(
            f"{SETTLEMENTS_URL}{self.settlement.pk}/pay/", {"tracking_code": "TRK-2"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_rejected(self):

        response = self.client.get(SETTLEMENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CommissionRuleViewSetTests(APITestCase):

    def setUp(self):

        self.staff = make_user("commission-staff", is_staff=True)
        self.resident = make_user("commission-resident")
        self.township = make_township()

    def test_any_authenticated_user_can_list(self):

        make_commission_rule(township=self.township)

        self.client.force_authenticate(self.resident)

        response = self.client.get(COMMISSION_RULES_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_staff_cannot_create(self):

        self.client.force_authenticate(self.resident)

        response = self.client.post(
            COMMISSION_RULES_URL,
            {"township": self.township.pk, "transaction_percent": "3", "monthly_subscription": "0"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_create(self):

        self.client.force_authenticate(self.staff)

        response = self.client.post(
            COMMISSION_RULES_URL,
            {"township": self.township.pk, "transaction_percent": "3", "monthly_subscription": "0"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_missing_township_rejected(self):

        self.client.force_authenticate(self.staff)

        response = self.client.post(
            COMMISSION_RULES_URL, {"transaction_percent": "3"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_rejected(self):

        response = self.client.get(COMMISSION_RULES_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CommissionTransactionViewSetTests(APITestCase):

    def setUp(self):

        self.township_owner = make_user("commission-township-owner")
        self.outsider = make_user("commission-outsider")
        self.staff = make_user("commission-tx-staff", is_staff=True)

        self.township = make_township()
        make_township_wallet(
            township=self.township, user=self.township_owner, balance=Decimal("0"),
        )

        rule = make_commission_rule(township=self.township)

        resident_wallet = make_resident_wallet(balance=Decimal("0"))
        wallet_transaction = WalletService.deposit(resident_wallet, Decimal("1000"))

        self.commission = CommissionTransaction.objects.create(
            wallet_transaction=wallet_transaction,
            township=self.township,
            amount=Decimal("20"),
            percent=rule.transaction_percent,
        )

    def test_township_owner_sees_own_township_commissions(self):

        self.client.force_authenticate(self.township_owner)

        response = self.client.get(COMMISSION_TRANSACTIONS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in (response.data["results"] if isinstance(response.data, dict) else response.data)}
        self.assertIn(self.commission.id, returned_ids)

    def test_outsider_sees_no_commissions(self):

        self.client.force_authenticate(self.outsider)

        response = self.client.get(COMMISSION_TRANSACTIONS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in (response.data["results"] if isinstance(response.data, dict) else response.data)}
        self.assertNotIn(self.commission.id, returned_ids)

    def test_staff_sees_all_commissions(self):

        self.client.force_authenticate(self.staff)

        response = self.client.get(COMMISSION_TRANSACTIONS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in (response.data["results"] if isinstance(response.data, dict) else response.data)}
        self.assertIn(self.commission.id, returned_ids)

    def test_read_only_rejects_write(self):

        self.client.force_authenticate(self.staff)

        response = self.client.post(COMMISSION_TRANSACTIONS_URL, {"amount": "1"})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
