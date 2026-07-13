"""
API tests for ``WalletViewSet`` and ``WalletTransactionViewSet``.
Paths match the router registrations in the project's ``urls.py``.
"""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from wallets.models import TransactionType, WalletTransaction
from wallets.services import WalletService

from .factories import make_resident_wallet, make_user

WALLETS_URL = "/wallets/wallets/"
TRANSACTIONS_URL = "/wallets/transactions/"


class WalletViewSetQuerysetTests(APITestCase):

    def setUp(self):

        self.alice = make_user("alice-wv")
        self.bob = make_user("bob-wv")
        self.staff = make_user("staff-wv", is_staff=True)

        self.alice_wallet = make_resident_wallet(user=self.alice, balance=Decimal("1000"))
        self.bob_wallet = make_resident_wallet(user=self.bob, balance=Decimal("500"))

    def test_owner_sees_only_own_wallets_in_list(self):

        self.client.force_authenticate(self.alice)

        response = self.client.get(WALLETS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in (response.data["results"] if isinstance(response.data, dict) else response.data)}
        self.assertIn(self.alice_wallet.id, returned_ids)
        self.assertNotIn(self.bob_wallet.id, returned_ids)

    def test_staff_sees_all_wallets(self):

        self.client.force_authenticate(self.staff)

        response = self.client.get(WALLETS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in (response.data["results"] if isinstance(response.data, dict) else response.data)}
        self.assertIn(self.alice_wallet.id, returned_ids)
        self.assertIn(self.bob_wallet.id, returned_ids)

    def test_retrieve_own_wallet_succeeds(self):

        self.client.force_authenticate(self.alice)

        response = self.client.get(f"{WALLETS_URL}{self.alice_wallet.pk}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["balance"]), Decimal("1000"))


class WalletDepositActionTests(APITestCase):

    def setUp(self):

        self.staff = make_user("finance-staff", is_staff=True)
        self.owner = make_user("wallet-owner")
        self.wallet = make_resident_wallet(user=self.owner, balance=Decimal("0"))

    def test_staff_can_deposit(self):

        self.client.force_authenticate(self.staff)

        response = self.client.post(
            f"{WALLETS_URL}{self.wallet.pk}/deposit/",
            {"amount": "500", "description": "manual credit"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["balance"]), Decimal("500"))

    def test_owner_cannot_deposit(self):

        self.client.force_authenticate(self.owner)

        response = self.client.post(
            f"{WALLETS_URL}{self.wallet.pk}/deposit/", {"amount": "500"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_deposit_requires_amount(self):

        self.client.force_authenticate(self.staff)

        response = self.client.post(f"{WALLETS_URL}{self.wallet.pk}/deposit/", {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deposit_rejects_zero_amount(self):

        self.client.force_authenticate(self.staff)

        response = self.client.post(
            f"{WALLETS_URL}{self.wallet.pk}/deposit/", {"amount": "0"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_deposit_rejected(self):

        response = self.client.post(
            f"{WALLETS_URL}{self.wallet.pk}/deposit/", {"amount": "500"},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class WalletWithdrawActionTests(APITestCase):

    def setUp(self):

        self.staff = make_user("finance-staff-2", is_staff=True)
        self.owner = make_user("wallet-owner-2")
        self.wallet = make_resident_wallet(user=self.owner, balance=Decimal("300"))

    def test_staff_can_withdraw(self):

        self.client.force_authenticate(self.staff)

        response = self.client.post(
            f"{WALLETS_URL}{self.wallet.pk}/withdraw/", {"amount": "100"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["balance"]), Decimal("200"))

    def test_withdraw_more_than_balance_returns_400_not_500(self):

        self.client.force_authenticate(self.staff)

        response = self.client.post(
            f"{WALLETS_URL}{self.wallet.pk}/withdraw/", {"amount": "10000"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("300"))

    def test_owner_cannot_withdraw(self):

        self.client.force_authenticate(self.owner)

        response = self.client.post(
            f"{WALLETS_URL}{self.wallet.pk}/withdraw/", {"amount": "100"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class WalletTransferActionTests(APITestCase):

    def setUp(self):

        self.alice = make_user("alice-transfer")
        self.bob = make_user("bob-transfer")

        self.alice_wallet = make_resident_wallet(user=self.alice, balance=Decimal("1000"))
        self.bob_wallet = make_resident_wallet(user=self.bob, balance=Decimal("0"))

    def test_transfer_to_self_rejected(self):

        self.client.force_authenticate(self.alice)

        response = self.client.post(
            f"{WALLETS_URL}{self.alice_wallet.pk}/transfer/",
            {"destination_wallet": self.alice_wallet.pk, "amount": "100"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_insufficient_balance_returns_400(self):

        self.client.force_authenticate(self.alice)

        response = self.client.post(
            f"{WALLETS_URL}{self.alice_wallet.pk}/transfer/",
            {"destination_wallet": self.bob_wallet.pk, "amount": "5000"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_to_unknown_wallet_rejected(self):

        self.client.force_authenticate(self.alice)

        response = self.client.post(
            f"{WALLETS_URL}{self.alice_wallet.pk}/transfer/",
            {"destination_wallet": 9999999, "amount": "100"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class WalletOnlineDepositActionTests(APITestCase):

    def setUp(self):

        self.owner = make_user("online-deposit-owner")
        self.wallet = make_resident_wallet(user=self.owner, balance=Decimal("0"))

    def test_no_active_gateway_returns_502(self):

        self.client.force_authenticate(self.owner)

        response = self.client.post(
            f"{WALLETS_URL}{self.wallet.pk}/online_deposit/", {"amount": "1000"},
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

        # A PENDING WalletTransaction row is created before the gateway
        # call and must remain — it will later be cleaned up by
        # CleanupService rather than silently vanishing.
        self.assertTrue(
            WalletTransaction.objects.filter(
                wallet=self.wallet,
                transaction_type=TransactionType.DEPOSIT,
                status=WalletTransaction.TransactionStatus.PENDING,
            ).exists()
        )

    def test_online_deposit_requires_amount(self):

        self.client.force_authenticate(self.owner)

        response = self.client.post(f"{WALLETS_URL}{self.wallet.pk}/online_deposit/", {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class WalletTransactionViewSetTests(APITestCase):

    def setUp(self):

        self.alice = make_user("alice-wt")
        self.bob = make_user("bob-wt")
        self.staff = make_user("staff-wt", is_staff=True)

        self.alice_wallet = make_resident_wallet(user=self.alice, balance=Decimal("0"))
        self.bob_wallet = make_resident_wallet(user=self.bob, balance=Decimal("0"))

        self.alice_transaction = WalletService.deposit(self.alice_wallet, Decimal("100"))
        self.bob_transaction = WalletService.deposit(self.bob_wallet, Decimal("200"))

    def test_owner_only_sees_own_transactions(self):

        self.client.force_authenticate(self.alice)

        response = self.client.get(TRANSACTIONS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in (response.data["results"] if isinstance(response.data, dict) else response.data)}
        self.assertIn(self.alice_transaction.id, returned_ids)
        self.assertNotIn(self.bob_transaction.id, returned_ids)

    def test_staff_sees_all_transactions(self):

        self.client.force_authenticate(self.staff)

        response = self.client.get(TRANSACTIONS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in (response.data["results"] if isinstance(response.data, dict) else response.data)}
        self.assertIn(self.alice_transaction.id, returned_ids)
        self.assertIn(self.bob_transaction.id, returned_ids)

    def test_read_only_viewset_rejects_post(self):

        self.client.force_authenticate(self.alice)

        response = self.client.post(TRANSACTIONS_URL, {"amount": "1"})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_cannot_retrieve_another_users_transaction(self):

        self.client.force_authenticate(self.alice)

        response = self.client.get(f"{TRANSACTIONS_URL}{self.bob_transaction.pk}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_by_transaction_type(self):

        self.client.force_authenticate(self.alice)
        WalletService.withdraw(self.alice_wallet, Decimal("10"))

        response = self.client.get(TRANSACTIONS_URL, {"transaction_type": "DEPOSIT"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = (response.data["results"] if isinstance(response.data, dict) else response.data)
        self.assertTrue(all(item["transaction_type"] == "DEPOSIT" for item in results))

    def test_ordering_by_amount(self):

        self.client.force_authenticate(self.alice)
        WalletService.deposit(self.alice_wallet, Decimal("50"))

        response = self.client.get(TRANSACTIONS_URL, {"ordering": "amount"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = (response.data["results"] if isinstance(response.data, dict) else response.data)
        amounts = [Decimal(item["amount"]) for item in results]
        self.assertEqual(amounts, sorted(amounts))

    def test_search_by_internal_reference(self):

        self.client.force_authenticate(self.alice)

        response = self.client.get(
            TRANSACTIONS_URL, {"search": self.alice_transaction.internal_reference},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = (response.data["results"] if isinstance(response.data, dict) else response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.alice_transaction.id)

    def test_unauthenticated_rejected(self):

        response = self.client.get(TRANSACTIONS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
