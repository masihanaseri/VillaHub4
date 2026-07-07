from django.contrib.auth import get_user_model

from django.db import IntegrityError

from django.test import TestCase

from django.utils import timezone

from gates.models import Gate

from townships.models import Township

from villas.models import Residence, Villa

from visitors.models import Visitor

from ..models import AccessLog

User = get_user_model()


class AccessLogModelTests(TestCase):

    def setUp(self):

        self.township = Township.objects.create(
            code="TS1",
            name="شهرک تست",
        )

        self.gate = Gate.objects.create(
            township=self.township,
            name="درب اصلی",
            code="MAIN",
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
        )

        self.residence = Residence.objects.create(
            user=self.resident_user,
            villa=self.villa,
            resident_type=Residence.ResidentType.OWNER,
            start_date=timezone.localdate(),
        )

        self.creator = User.objects.create_user(
            username="creator1",
            password="StrongPass123",
            mobile="09120000002",
        )

        self.visitor = Visitor.objects.create(
            township=self.township,
            residence=self.residence,
            created_by=self.creator,
            full_name="مهمان تست",
            mobile="09121112233",
            valid_from=timezone.now(),
            valid_until=timezone.now() + timezone.timedelta(days=1),
        )

    def test_str_with_visitor(self):

        log = AccessLog.objects.create(
            township=self.township,
            gate=self.gate,
            visitor=self.visitor,
            direction=AccessLog.Direction.IN,
        )

        self.assertIn("مهمان تست", str(log))

    def test_subject_display_with_residence(self):

        log = AccessLog.objects.create(
            township=self.township,
            gate=self.gate,
            residence=self.residence,
            direction=AccessLog.Direction.IN,
        )

        self.assertIn("ساکن:", log.subject_display)

    def test_subject_display_unknown(self):

        log = AccessLog.objects.create(
            township=self.township,
            gate=self.gate,
            direction=AccessLog.Direction.IN,
        )

        self.assertEqual(log.subject_display, "نامشخص")

    def test_cannot_have_both_visitor_and_residence(self):

        with self.assertRaises(IntegrityError):

            AccessLog.objects.create(
                township=self.township,
                gate=self.gate,
                visitor=self.visitor,
                residence=self.residence,
                direction=AccessLog.Direction.IN,
            )

    def test_manager_entries_and_exits(self):

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

        self.assertEqual(AccessLog.objects.entries().count(), 1)

        self.assertEqual(AccessLog.objects.exits().count(), 1)

    def test_gate_deletion_is_protected_when_logs_exist(self):

        AccessLog.objects.create(
            township=self.township,
            gate=self.gate,
            direction=AccessLog.Direction.IN,
        )

        with self.assertRaises(Exception):

            self.gate.delete()
