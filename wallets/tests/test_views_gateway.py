"""
Paths match the router registrations in the project's ``urls.py``
(note ``PaymentGatewayViewSet`` is registered as "payment-gateways").
"""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from wallets.models import GatewayCallback, GatewayTransaction

from .factories import make_gateway, make_resident_wallet, make_user

GATEWAYS_URL = "/wallets/payment-gateways/"
GATEWAY_TRANSACTIONS_URL = "/wallets/gateway-transactions/"
GATEWAY_CALLBACKS_URL = "/wallets/gateway-callbacks/"


class PaymentGatewayViewSetTests(APITestCase):

    def setUp(self):

        self.staff = make_user("gateway-staff", is_staff=True)
        self.resident = make_user("gateway-resident")
        self.gateway = make_gateway()

    def test_any_authenticated_user_can_list(self):

        self.client.force_authenticate(self.resident)

        response = self.client.get(GATEWAYS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_secrets_are_not_exposed_in_list(self):

        self.client.force_authenticate(self.resident)

        response = self.client.get(GATEWAYS_URL)

        results = (response.data["results"] if isinstance(response.data, dict) else response.data)
        for item in results:
            self.assertNotIn("merchant_id", item)
            self.assertNotIn("api_key", item)

    def test_non_staff_cannot_create_gateway(self):

        self.client.force_authenticate(self.resident)

        response = self.client.post(
            GATEWAYS_URL,
            {"name": "New Gateway", "slug": "new-gateway", "merchant_id": "x", "priority": 1},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_create_gateway(self):

        self.client.force_authenticate(self.staff)

        response = self.client.post(
            GATEWAYS_URL,
            {"name": "New Gateway", "slug": "new-gateway-2", "merchant_id": "x", "priority": 1},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unauthenticated_rejected(self):

        response = self.client.get(GATEWAYS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class GatewayTransactionViewSetTests(APITestCase):

    def setUp(self):

        self.alice = make_user("alice-gt")
        self.bob = make_user("bob-gt")
        self.staff = make_user("staff-gt", is_staff=True)

        self.alice_wallet = make_resident_wallet(user=self.alice, balance=Decimal("0"))
        self.bob_wallet = make_resident_wallet(user=self.bob, balance=Decimal("0"))

        self.gateway = make_gateway()

        self.alice_gt = GatewayTransaction.objects.create(
            wallet=self.alice_wallet, gateway=self.gateway, amount=Decimal("100"),
            authority="A-ALICE",
        )
        self.bob_gt = GatewayTransaction.objects.create(
            wallet=self.bob_wallet, gateway=self.gateway, amount=Decimal("200"),
            authority="A-BOB",
        )

    def test_owner_only_sees_own_gateway_transactions(self):

        self.client.force_authenticate(self.alice)

        response = self.client.get(GATEWAY_TRANSACTIONS_URL)

        returned_ids = {item["id"] for item in (response.data["results"] if isinstance(response.data, dict) else response.data)}
        self.assertIn(self.alice_gt.id, returned_ids)
        self.assertNotIn(self.bob_gt.id, returned_ids)

    def test_staff_sees_all(self):

        self.client.force_authenticate(self.staff)

        response = self.client.get(GATEWAY_TRANSACTIONS_URL)

        returned_ids = {item["id"] for item in (response.data["results"] if isinstance(response.data, dict) else response.data)}
        self.assertIn(self.alice_gt.id, returned_ids)
        self.assertIn(self.bob_gt.id, returned_ids)

    def test_cannot_retrieve_others_gateway_transaction(self):

        self.client.force_authenticate(self.alice)

        response = self.client.get(f"{GATEWAY_TRANSACTIONS_URL}{self.bob_gt.pk}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_verification_fields_read_only_end_to_end(self):
        """
        Even though this is a ReadOnlyModelViewSet (writes are already
        blocked at the routing level), the serializer itself must also
        keep verification fields read-only as defense in depth.
        """

        self.client.force_authenticate(self.alice)

        response = self.client.put(
            f"{GATEWAY_TRANSACTIONS_URL}{self.alice_gt.pk}/", {"is_success": True},
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_filter_by_gateway(self):

        self.client.force_authenticate(self.staff)

        response = self.client.get(GATEWAY_TRANSACTIONS_URL, {"gateway": self.gateway.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_rejected(self):

        response = self.client.get(GATEWAY_TRANSACTIONS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class GatewayCallbackViewSetTests(APITestCase):

    def setUp(self):

        self.staff = make_user("callback-staff", is_staff=True)
        self.resident = make_user("callback-resident")

        wallet = make_resident_wallet(user=self.resident, balance=Decimal("0"))
        gateway = make_gateway()
        gateway_transaction = GatewayTransaction.objects.create(
            wallet=wallet, gateway=gateway, amount=Decimal("100"), authority="A-CB",
        )

        self.callback = GatewayCallback.objects.create(
            gateway_transaction=gateway_transaction, raw_data={"Authority": "A-CB"},
        )

    def test_finance_staff_can_list(self):

        self.client.force_authenticate(self.staff)

        response = self.client.get(GATEWAY_CALLBACKS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_resident_forbidden(self):

        self.client.force_authenticate(self.resident)

        response = self.client.get(GATEWAY_CALLBACKS_URL)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_rejected(self):

        response = self.client.get(GATEWAY_CALLBACKS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_write_not_allowed(self):

        self.client.force_authenticate(self.staff)

        response = self.client.post(GATEWAY_CALLBACKS_URL, {"raw_data": {}}, format="json")

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
