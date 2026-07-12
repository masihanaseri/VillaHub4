from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from .factories import make_resident_wallet, make_user


class WalletPermissionTests(APITestCase):

    def setUp(self):

        self.alice = make_user("alice")
        self.bob = make_user("bob")

        self.alice_wallet = make_resident_wallet(user=self.alice, balance=Decimal("1000"))
        self.bob_wallet = make_resident_wallet(user=self.bob, balance=Decimal("1000"))

    def test_user_cannot_view_another_users_wallet(self):

        self.client.force_authenticate(self.alice)

        response = self.client.get(f"/wallets/wallets/{self.bob_wallet.pk}/")

        self.assertIn(
            response.status_code,
            (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN),
        )

    def test_user_cannot_transfer_from_another_users_wallet(self):

        self.client.force_authenticate(self.alice)

        response = self.client.post(
            f"/wallets/wallets/{self.bob_wallet.pk}/transfer/",
            {"destination_wallet": self.alice_wallet.pk, "amount": "100"},
        )

        self.assertIn(
            response.status_code,
            (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN),
        )

        self.bob_wallet.refresh_from_db()
        self.assertEqual(self.bob_wallet.balance, Decimal("1000"))

    def test_owner_can_transfer_from_own_wallet(self):

        self.client.force_authenticate(self.alice)

        response = self.client.post(
            f"/wallets/wallets/{self.alice_wallet.pk}/transfer/",
            {"destination_wallet": self.bob_wallet.pk, "amount": "100"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.alice_wallet.refresh_from_db()
        self.bob_wallet.refresh_from_db()

        self.assertEqual(self.alice_wallet.balance, Decimal("900"))
        self.assertEqual(self.bob_wallet.balance, Decimal("1100"))

    def test_non_staff_cannot_manually_deposit(self):

        self.client.force_authenticate(self.alice)

        response = self.client.post(
            f"/wallets/wallets/{self.alice_wallet.pk}/deposit/",
            {"amount": "500"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_request_rejected(self):

        response = self.client.get(f"/wallets/wallets/{self.alice_wallet.pk}/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
