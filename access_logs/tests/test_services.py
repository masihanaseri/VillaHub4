from django.contrib.auth import get_user_model

from django.test import TestCase

from django.utils import timezone

from gates.models import Gate

from guards.models import Guard

from rest_framework.exceptions import ValidationError

from townships.models import Township

from villas.models import Residence, Villa

from visitors.models import Visitor

from visitors.services import VisitorService

from ..models import AccessLog

from ..services import AccessLogService

User = get_user_model()


class AccessLogServiceTests(TestCase):

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

        self.foreign_gate = Gate.objects.create(
            township=self.other_township,
            name="درب دیگری",
            code="OTHER",
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

        self.foreign_guard_user = User.objects.create_user(
            username="foreignguard",
            password="StrongPass123",
            mobile="09120000010",
        )

        self.foreign_guard = Guard.objects.create(
            township=self.other_township,
            user=self.foreign_guard_user,
            employee_code="G-2",
            phone="09121112233",
            shift=Guard.Shift.EVENING,
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

    def test_record_entry_for_residence(self):

        log = AccessLogService.record_entry(
            gate=self.gate,
            guard=self.guard,
            residence=self.residence,
        )

        self.assertEqual(log.direction, AccessLog.Direction.IN)

        self.assertEqual(log.township, self.township)

    def test_record_entry_for_visitor_syncs_visitor_status(self):

        VisitorService.approve(
            self.visitor,
            approved_by=self.creator,
        )

        AccessLogService.record_entry(
            gate=self.gate,
            guard=self.guard,
            visitor=self.visitor,
        )

        self.visitor.refresh_from_db()

        self.assertEqual(
            self.visitor.status,
            Visitor.VisitorStatus.CHECKED_IN,
        )

    def test_record_entry_for_unapproved_visitor_still_creates_log(self):
        """
        اگر مهمان هنوز تایید نشده، VisitorService.check_in شکست می‌خورد
        اما ثبت فیزیکی تردد (AccessLog) نباید به‌خاطر این اختلاف اداری
        رد شود.
        """

        log = AccessLogService.record_entry(
            gate=self.gate,
            guard=self.guard,
            visitor=self.visitor,
        )

        self.assertIsNotNone(log.pk)

        self.visitor.refresh_from_db()

        self.assertEqual(
            self.visitor.status,
            Visitor.VisitorStatus.REQUESTED,
        )

    def test_record_on_inactive_gate_raises(self):

        self.gate.is_active = False

        self.gate.save()

        with self.assertRaises(ValidationError):

            AccessLogService.record_entry(
                gate=self.gate,
                guard=self.guard,
            )

    def test_guard_from_other_township_raises(self):

        with self.assertRaises(ValidationError):

            AccessLogService.record_entry(
                gate=self.gate,
                guard=self.foreign_guard,
            )

    def test_visitor_and_residence_together_raises(self):

        with self.assertRaises(ValidationError):

            AccessLogService.record_entry(
                gate=self.gate,
                guard=self.guard,
                visitor=self.visitor,
                residence=self.residence,
            )

    def test_residence_from_other_township_raises(self):

        with self.assertRaises(ValidationError):

            AccessLogService.record_entry(
                gate=self.foreign_gate,
                residence=self.residence,
            )

    def test_record_exit(self):

        log = AccessLogService.record_exit(
            gate=self.gate,
            guard=self.guard,
            residence=self.residence,
        )

        self.assertEqual(log.direction, AccessLog.Direction.OUT)
