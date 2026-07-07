from django.contrib.auth import get_user_model

from django.test import TestCase

from rest_framework.exceptions import ValidationError

from gates.models import Gate

from townships.models import Township

from ..models import Guard

from ..services import GuardService

User = get_user_model()


class GuardServiceTests(TestCase):

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
            username="guard1",
            password="StrongPass123",
            mobile="09120000001",
        )

        self.guard = Guard.objects.create(
            township=self.township,
            user=self.user,
            employee_code="G-001",
            phone="09121112233",
            shift=Guard.Shift.MORNING,
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

    # ------------------------------------------------
    # Shift
    # ------------------------------------------------

    def test_start_and_end_shift(self):

        shift = GuardService.start_shift(self.guard)

        self.assertTrue(shift.is_open)

        GuardService.end_shift(self.guard)

        shift.refresh_from_db()

        self.assertFalse(shift.is_open)

    def test_start_shift_twice_raises(self):

        GuardService.start_shift(self.guard)

        with self.assertRaises(ValidationError):

            GuardService.start_shift(self.guard)

    def test_end_shift_without_open_shift_raises(self):

        with self.assertRaises(ValidationError):

            GuardService.end_shift(self.guard)

    def test_start_shift_for_inactive_guard_raises(self):

        GuardService.deactivate(self.guard)

        with self.assertRaises(ValidationError):

            GuardService.start_shift(self.guard)

    # ------------------------------------------------
    # Activate / deactivate
    # ------------------------------------------------

    def test_deactivate_closes_open_shift(self):

        GuardService.start_shift(self.guard)

        GuardService.deactivate(self.guard)

        self.guard.refresh_from_db()

        self.assertFalse(self.guard.is_active)

        self.assertFalse(self.guard.has_active_shift)

    def test_activate_already_active_raises(self):

        with self.assertRaises(ValidationError):

            GuardService.activate(self.guard)

    # ------------------------------------------------
    # Gate assignment
    # ------------------------------------------------

    def test_assign_and_remove_gate(self):

        GuardService.assign_gate(
            guard=self.guard,
            gate=self.gate,
        )

        self.assertIn(
            self.gate,
            self.guard.gates.all(),
        )

        GuardService.remove_gate(
            guard=self.guard,
            gate=self.gate,
        )

        self.assertNotIn(
            self.gate,
            self.guard.gates.all(),
        )

    def test_assign_gate_from_other_township_raises(self):

        with self.assertRaises(ValidationError):

            GuardService.assign_gate(
                guard=self.guard,
                gate=self.foreign_gate,
            )

    def test_assign_duplicate_gate_raises(self):

        GuardService.assign_gate(
            guard=self.guard,
            gate=self.gate,
        )

        with self.assertRaises(ValidationError):

            GuardService.assign_gate(
                guard=self.guard,
                gate=self.gate,
            )

    def test_remove_unassigned_gate_raises(self):

        with self.assertRaises(ValidationError):

            GuardService.remove_gate(
                guard=self.guard,
                gate=self.gate,
            )
