from django.contrib.auth import get_user_model

from django.test import TestCase

from rest_framework import status

from rest_framework.test import APIClient

from gates.models import Gate

from townships.models import Township

from ..models import Guard

User = get_user_model()


class GuardAPITests(TestCase):

    def setUp(self):

        self.township = Township.objects.create(
            code="TS1",
            name="شهرک تست",
        )

        self.other_township = Township.objects.create(
            code="TS2",
            name="شهرک دیگر",
        )

        self.resident = User.objects.create_user(
            username="resident1",
            password="StrongPass123",
            mobile="09120000001",
            active_township=self.township,
        )

        self.guard_user = User.objects.create_user(
            username="guarduser",
            password="StrongPass123",
            mobile="09120000002",
        )

        self.gate = Gate.objects.create(
            township=self.township,
            name="درب اصلی",
            code="MAIN",
        )

        self.client = APIClient()

        self.client.force_authenticate(
            user=self.resident,
        )

        self.list_url = "/api/guards/"

    def test_create_guard(self):

        payload = {
            "user": self.guard_user.id,
            "employee_code": "G-001",
            "phone": "09121112233",
            "shift": Guard.Shift.MORNING,
        }

        response = self.client.post(
            self.list_url,
            payload,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        guard = Guard.objects.get(
            employee_code="G-001",
        )

        self.assertEqual(guard.township, self.township)

    def test_list_only_returns_active_township_guards(self):

        Guard.objects.create(
            township=self.township,
            user=self.guard_user,
            employee_code="G-1",
            phone="09121112233",
            shift=Guard.Shift.MORNING,
        )

        other_user = User.objects.create_user(
            username="otherguard",
            password="StrongPass123",
            mobile="09120000003",
        )

        Guard.objects.create(
            township=self.other_township,
            user=other_user,
            employee_code="G-2",
            phone="09121112233",
            shift=Guard.Shift.EVENING,
        )

        response = self.client.get(self.list_url)

        codes = [item["employee_code"] for item in response.data]

        self.assertEqual(codes, ["G-1"])

    def test_start_and_end_shift_actions(self):

        guard = Guard.objects.create(
            township=self.township,
            user=self.guard_user,
            employee_code="G-1",
            phone="09121112233",
            shift=Guard.Shift.MORNING,
        )

        start_response = self.client.post(
            f"{self.list_url}{guard.id}/start_shift/",
        )

        self.assertEqual(
            start_response.status_code,
            status.HTTP_200_OK,
            start_response.data,
        )

        self.assertTrue(start_response.data["has_active_shift"])

        end_response = self.client.post(
            f"{self.list_url}{guard.id}/end_shift/",
        )

        self.assertEqual(
            end_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(end_response.data["has_active_shift"])

    def test_assign_and_remove_gate_actions(self):

        guard = Guard.objects.create(
            township=self.township,
            user=self.guard_user,
            employee_code="G-1",
            phone="09121112233",
            shift=Guard.Shift.MORNING,
        )

        assign_response = self.client.post(
            f"{self.list_url}{guard.id}/assign_gate/",
            {"gate_id": self.gate.id},
        )

        self.assertEqual(
            assign_response.status_code,
            status.HTTP_200_OK,
            assign_response.data,
        )

        self.assertIn(
            self.gate.id,
            assign_response.data["gates"],
        )

        remove_response = self.client.post(
            f"{self.list_url}{guard.id}/remove_gate/",
            {"gate_id": self.gate.id},
        )

        self.assertEqual(
            remove_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertNotIn(
            self.gate.id,
            remove_response.data["gates"],
        )

    def test_cannot_access_guard_of_another_township(self):

        other_user = User.objects.create_user(
            username="otherguard",
            password="StrongPass123",
            mobile="09120000003",
        )

        foreign_guard = Guard.objects.create(
            township=self.other_township,
            user=other_user,
            employee_code="G-2",
            phone="09121112233",
            shift=Guard.Shift.EVENING,
        )

        response = self.client.get(
            f"{self.list_url}{foreign_guard.id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
