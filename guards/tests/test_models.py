from django.contrib.auth import get_user_model

from django.db import IntegrityError

from django.test import TestCase

from django.utils import timezone

from townships.models import Township

from ..models import Guard, GuardShift

User = get_user_model()


class GuardModelTests(TestCase):

    def setUp(self):

        self.township = Township.objects.create(
            code="TS1",
            name="شهرک تست",
        )

        self.user = User.objects.create_user(
            username="guard1",
            password="StrongPass123",
            mobile="09120000001",
            first_name="علی",
            last_name="محمدی",
        )

    def test_str_uses_get_full_name(self):

        guard = Guard.objects.create(
            township=self.township,
            user=self.user,
            employee_code="g-001",
            phone="09121112233",
            shift=Guard.Shift.MORNING,
        )

        self.assertEqual(
            str(guard),
            "علی محمدی (G-001)",
        )

    def test_str_falls_back_to_username_without_full_name(self):

        user = User.objects.create_user(
            username="noname",
            password="StrongPass123",
            mobile="09120000002",
        )

        guard = Guard.objects.create(
            township=self.township,
            user=user,
            employee_code="G-002",
            phone="09121112233",
            shift=Guard.Shift.EVENING,
        )

        self.assertEqual(
            str(guard),
            "noname (G-002)",
        )

    def test_employee_code_normalized_to_uppercase(self):

        guard = Guard.objects.create(
            township=self.township,
            user=self.user,
            employee_code="g-abc",
            phone="09121112233",
            shift=Guard.Shift.NIGHT,
        )

        self.assertEqual(guard.employee_code, "G-ABC")

    def test_ordering_does_not_raise(self):
        """
        رگرسیون باگ قبلی: ordering = ["user__full_name"] که چون فیلدی به این
        نام روی User وجود نداشت، خطای E015 در system check ایجاد می‌کرد.
        """

        Guard.objects.create(
            township=self.township,
            user=self.user,
            employee_code="G-003",
            phone="09121112233",
            shift=Guard.Shift.MORNING,
        )

        guards = list(Guard.objects.all())

        self.assertEqual(len(guards), 1)

    def test_only_one_open_shift_allowed(self):

        guard = Guard.objects.create(
            township=self.township,
            user=self.user,
            employee_code="G-004",
            phone="09121112233",
            shift=Guard.Shift.MORNING,
        )

        GuardShift.objects.create(
            guard=guard,
            started_at=timezone.now(),
        )

        with self.assertRaises(IntegrityError):

            GuardShift.objects.create(
                guard=guard,
                started_at=timezone.now(),
            )

    def test_has_active_shift_property(self):

        guard = Guard.objects.create(
            township=self.township,
            user=self.user,
            employee_code="G-005",
            phone="09121112233",
            shift=Guard.Shift.MORNING,
        )

        self.assertFalse(guard.has_active_shift)

        GuardShift.objects.create(
            guard=guard,
            started_at=timezone.now(),
        )

        self.assertTrue(guard.has_active_shift)
