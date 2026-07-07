from django.contrib.auth import get_user_model

from django.test import TestCase

from django.utils import timezone

from rest_framework import status

from rest_framework.test import APIClient

from gates.models import Gate

from guards.models import Guard

from townships.models import Township

from villas.models import Residence, Villa

from ..models import AccessLog

User = get_user_model()


class AccessLogAPITests(TestCase):

    def setUp(self):

        self.township = Township.objects.create(
            code="TS1",
            name="شهرک تست",
        )

        self.other_township = Township.objects.create(
            code="TS2",
            name="شهرک دیگر",
        )

        self.gate = Gate.objects.create(
            township=self.township,
            name="درب اصلی",
            code="MAIN",
        )

        guard_user = User.objects.create_user(
            username="guarduser",
            password="StrongPass123",
            mobile="09120000009",
        )

        self.guard = Guard.objects.create(
            township=self.township,
            user=guard_user,
            employee_code="G-1",
            phone="09121112233",
            shift=Guard.Shift.MORNING,
        )

        self.villa = Villa.objects.create(
            township=self.township,
            code="V-1",
            name="ویلا یک",
            area="200.00",
        )

        self.resident_user = User.objects.create_user(
            username="resident1",
            password="StrongPass123",
            mobile="09120000001",
            active_township=self.township,
        )

        self.residence = Residence.objects.create(
            user=self.resident_user,
            villa=self.villa,
            resident_type=Residence.ResidentType.OWNER,
            start_date=timezone.localdate(),
        )

        self.client = APIClient()

        self.client.force_authenticate(
            user=self.resident_user,
        )

        self.list_url = "/api/access-logs/"

    def test_entry_action_creates_log(self):

        payload = {
            "gate": self.gate.id,
            "guard": self.guard.id,
            "residence": self.residence.id,
        }

        response = self.client.post(
            f"{self.list_url}entry/",
            payload,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        self.assertEqual(
            AccessLog.objects.count(),
            1,
        )

        self.assertEqual(
            AccessLog.objects.first().direction,
            AccessLog.Direction.IN,
        )

    def test_exit_action_creates_log(self):

        payload = {
            "gate": self.gate.id,
            "residence": self.residence.id,
        }

        response = self.client.post(
            f"{self.list_url}exit/",
            payload,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            AccessLog.objects.first().direction,
            AccessLog.Direction.OUT,
        )

    def test_list_only_returns_active_township_logs(self):

        AccessLog.objects.create(
            township=self.township,
            gate=self.gate,
            direction=AccessLog.Direction.IN,
        )

        foreign_gate = Gate.objects.create(
            township=self.other_township,
            name="درب دیگری",
            code="OTHER",
        )

        AccessLog.objects.create(
            township=self.other_township,
            gate=foreign_gate,
            direction=AccessLog.Direction.IN,
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_update_is_not_allowed(self):

        log = AccessLog.objects.create(
            township=self.township,
            gate=self.gate,
            direction=AccessLog.Direction.IN,
        )

        response = self.client.patch(
            f"{self.list_url}{log.id}/",
            {"notes": "تلاش برای ویرایش"},
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_403_FORBIDDEN,
                status.HTTP_405_METHOD_NOT_ALLOWED,
            ),
        )

    def test_delete_is_not_allowed(self):

        log = AccessLog.objects.create(
            township=self.township,
            gate=self.gate,
            direction=AccessLog.Direction.IN,
        )

        response = self.client.delete(
            f"{self.list_url}{log.id}/",
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_403_FORBIDDEN,
                status.HTTP_405_METHOD_NOT_ALLOWED,
            ),
        )

    def test_filter_by_direction(self):

        AccessLog.objects.create(
            township=self.township,
            gate=self.gate,
            direction=AccessLog.Direction.IN,
        )

        AccessLog.objects.create(
            township=self.township,
            gate=self.gate,
            direction=AccessLog.Direction.OUT,
        )

        response = self.client.get(
            self.list_url,
            {"direction": "OUT"},
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        self.assertEqual(
            response.data[0]["direction"],
            "OUT",
        )
