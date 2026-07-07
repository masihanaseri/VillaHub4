from django.contrib.auth import get_user_model

from django.test import TestCase

from rest_framework import status

from rest_framework.test import APIClient

from townships.models import Township

from ..models import Gate

User = get_user_model()


class GateAPITests(TestCase):

    def setUp(self):

        self.township = Township.objects.create(
            code="TS1",
            name="شهرک تست",
        )

        self.other_township = Township.objects.create(
            code="TS2",
            name="شهرک دیگر",
        )

        self.user = User.objects.create_user(
            username="resident1",
            password="StrongPass123",
            mobile="09120000001",
            active_township=self.township,
        )

        self.client = APIClient()

        self.client.force_authenticate(
            user=self.user,
        )

        self.list_url = "/api/gates/"

    def test_list_requires_authentication(self):
        """
        توجه: چون SessionAuthentication کاربر مهمان را «AnonymousUser موفق»
        در نظر می‌گیرد (نه شکست احراز هویت)، DRF در این پروژه برای درخواست‌های
        بدون لاگین کد 403 برمی‌گرداند، نه 401. این رفتار در تمام اپ‌های پروژه
        (reservations، visitors) یکسان است.
        """

        anonymous_client = APIClient()

        response = anonymous_client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_create_gate(self):

        payload = {
            "name": "درب اصلی",
            "code": "MAIN-1",
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

        self.assertEqual(
            Gate.objects.count(),
            1,
        )

        gate = Gate.objects.first()

        self.assertEqual(gate.township, self.township)

    def test_list_only_returns_active_township_gates(self):

        Gate.objects.create(
            township=self.township,
            name="درب من",
            code="MINE",
        )

        Gate.objects.create(
            township=self.other_township,
            name="درب دیگری",
            code="OTHER",
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        codes = [item["code"] for item in response.data]

        self.assertEqual(codes, ["MINE"])

    def test_activate_deactivate_actions(self):

        gate = Gate.objects.create(
            township=self.township,
            name="درب",
            code="G-1",
        )

        deactivate_response = self.client.post(
            f"{self.list_url}{gate.id}/deactivate/",
        )

        self.assertEqual(
            deactivate_response.status_code,
            status.HTTP_200_OK,
        )

        gate.refresh_from_db()

        self.assertFalse(gate.is_active)

        activate_response = self.client.post(
            f"{self.list_url}{gate.id}/activate/",
        )

        self.assertEqual(
            activate_response.status_code,
            status.HTTP_200_OK,
        )

        gate.refresh_from_db()

        self.assertTrue(gate.is_active)

    def test_cannot_access_gate_of_another_township(self):

        foreign_gate = Gate.objects.create(
            township=self.other_township,
            name="درب دیگری",
            code="OTHER",
        )

        response = self.client.get(
            f"{self.list_url}{foreign_gate.id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_filter_by_is_active(self):

        Gate.objects.create(
            township=self.township,
            name="درب فعال",
            code="ACTIVE-1",
            is_active=True,
        )

        Gate.objects.create(
            township=self.township,
            name="درب غیرفعال",
            code="INACTIVE-1",
            is_active=False,
        )

        response = self.client.get(
            self.list_url,
            {"is_active": "false"},
        )

        codes = [item["code"] for item in response.data]

        self.assertEqual(codes, ["INACTIVE-1"])
