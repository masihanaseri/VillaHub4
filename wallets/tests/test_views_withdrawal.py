"""
Paths match the router registrations in the project's ``urls.py``
(note ``WithdrawalRequestViewSet`` is registered as "withdraw-requests").
"""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from wallets.models import WithdrawalRequest

from .factories import make_resident_wallet, make_user

WITHDRAWALS_URL = "/wallets/withdraw-requests/"


class WithdrawalRequestCreateActionTests(APITestCase):

    def setUp(self):

        self.owner = make_user("withdrawal-view-owner")
        self.wallet = make_resident_wallet(user=self.owner, balance=Decimal("2000"))

    def test_owner_can_request_withdrawal(self):

        self.client.force_authenticate(self.owner)

        response = self.client.post(
            f"{WITHDRAWALS_URL}create_request/",
            {"amount": "1000", "bank_name": "Test Bank", "iban": "IR000000000000000000000001"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertEqual(Decimal(response.data["amount"]), Decimal("1000"))

    def test_insufficient_balance_returns_400(self):

        self.client.force_authenticate(self.owner)

        response = self.client.post(
            f"{WITHDRAWALS_URL}create_request/", {"amount": "5000"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_amount_returns_400(self):

        self.client.force_authenticate(self.owner)

        response = self.client.post(f"{WITHDRAWALS_URL}create_request/", {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_rejected(self):

        response = self.client.post(
            f"{WITHDRAWALS_URL}create_request/", {"amount": "1000"},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class WithdrawalRequestListTests(APITestCase):

    def setUp(self):

        self.alice = make_user("alice-wr")
        self.bob = make_user("bob-wr")
        self.staff = make_user("staff-wr", is_staff=True)

        self.alice_wallet = make_resident_wallet(user=self.alice, balance=Decimal("2000"))
        self.bob_wallet = make_resident_wallet(user=self.bob, balance=Decimal("2000"))

        self.client.force_authenticate(self.alice)
        alice_response = self.client.post(
            f"{WITHDRAWALS_URL}create_request/", {"amount": "500"},
        )
        self.alice_request_id = alice_response.data["id"]

        self.client.force_authenticate(self.bob)
        bob_response = self.client.post(
            f"{WITHDRAWALS_URL}create_request/", {"amount": "700"},
        )
        self.bob_request_id = bob_response.data["id"]

    def test_owner_sees_only_own_requests(self):

        self.client.force_authenticate(self.alice)

        response = self.client.get(WITHDRAWALS_URL)

        returned_ids = {item["id"] for item in (response.data["results"] if isinstance(response.data, dict) else response.data)}
        self.assertIn(self.alice_request_id, returned_ids)
        self.assertNotIn(self.bob_request_id, returned_ids)

    def test_staff_sees_all_requests(self):

        self.client.force_authenticate(self.staff)

        response = self.client.get(WITHDRAWALS_URL)

        returned_ids = {item["id"] for item in (response.data["results"] if isinstance(response.data, dict) else response.data)}
        self.assertIn(self.alice_request_id, returned_ids)
        self.assertIn(self.bob_request_id, returned_ids)

    def test_filter_by_status(self):

        self.client.force_authenticate(self.staff)

        response = self.client.get(WITHDRAWALS_URL, {"status": "PENDING"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = (response.data["results"] if isinstance(response.data, dict) else response.data)
        self.assertTrue(all(item["status"] == "PENDING" for item in results))

    def test_ordering_by_created_at_desc(self):

        self.client.force_authenticate(self.staff)

        response = self.client.get(WITHDRAWALS_URL, {"ordering": "-created_at"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class WithdrawalRequestApprovePayRejectTests(APITestCase):

    def setUp(self):

        self.owner = make_user("withdrawal-lifecycle-owner")
        self.wallet = make_resident_wallet(user=self.owner, balance=Decimal("5000"))
        self.staff = make_user("withdrawal-lifecycle-staff", is_staff=True)

        self.client.force_authenticate(self.owner)
        create_response = self.client.post(
            f"{WITHDRAWALS_URL}create_request/", {"amount": "2000"},
        )
        self.request_id = create_response.data["id"]

    def test_owner_cannot_approve_own_request(self):

        self.client.force_authenticate(self.owner)

        response = self.client.post(f"{WITHDRAWALS_URL}{self.request_id}/approve/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_approve_then_pay(self):

        self.client.force_authenticate(self.staff)

        approve_response = self.client.post(f"{WITHDRAWALS_URL}{self.request_id}/approve/")
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data["status"], "APPROVED")

        pay_response = self.client.post(
            f"{WITHDRAWALS_URL}{self.request_id}/pay/", {"tracking_code": "TRK-W-1"},
        )
        self.assertEqual(pay_response.status_code, status.HTTP_200_OK)
        self.assertEqual(pay_response.data["status"], "PAID")

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("3000"))

    def test_pay_before_approval_returns_400(self):

        self.client.force_authenticate(self.staff)

        response = self.client.post(
            f"{WITHDRAWALS_URL}{self.request_id}/pay/", {"tracking_code": "TRK-W-2"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_can_reject_pending_request(self):

        self.client.force_authenticate(self.staff)

        response = self.client.post(
            f"{WITHDRAWALS_URL}{self.request_id}/reject/", {"reason": "Suspicious activity"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "REJECTED")

        withdrawal_request = WithdrawalRequest.objects.get(pk=self.request_id)
        self.assertEqual(withdrawal_request.reject_reason, "Suspicious activity")

    def test_reject_releases_no_balance_since_none_was_reserved(self):

        self.client.force_authenticate(self.staff)
        self.client.post(f"{WITHDRAWALS_URL}{self.request_id}/reject/", {"reason": "no"})

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("5000"))

    def test_cannot_reject_already_paid_request(self):

        self.client.force_authenticate(self.staff)
        self.client.post(f"{WITHDRAWALS_URL}{self.request_id}/approve/")
        self.client.post(
            f"{WITHDRAWALS_URL}{self.request_id}/pay/", {"tracking_code": "TRK-W-3"},
        )

        response = self.client.post(
            f"{WITHDRAWALS_URL}{self.request_id}/reject/", {"reason": "too late"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_staff_cannot_reject(self):

        self.client.force_authenticate(self.owner)

        response = self.client.post(
            f"{WITHDRAWALS_URL}{self.request_id}/reject/", {"reason": "no"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
