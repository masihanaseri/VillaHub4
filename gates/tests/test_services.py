from rest_framework.exceptions import ValidationError

from django.test import TestCase

from townships.models import Township

from ..models import Gate

from ..services import GateService


class GateServiceTests(TestCase):

    def setUp(self):

        self.township = Township.objects.create(
            code="TS1",
            name="شهرک تست",
        )

    def test_create_gate(self):

        gate = GateService.create(
            township=self.township,
            name="درب شمالی",
            code="north-1",
        )

        self.assertEqual(gate.code, "NORTH-1")

        self.assertTrue(gate.is_active)

    def test_create_without_township_raises(self):

        with self.assertRaises(ValidationError):

            GateService.create(
                township=None,
                name="درب",
                code="G-1",
            )

    def test_create_duplicate_code_raises_validation_error(self):

        GateService.create(
            township=self.township,
            name="درب اول",
            code="G-1",
        )

        with self.assertRaises(ValidationError):

            GateService.create(
                township=self.township,
                name="درب دوم",
                code="G-1",
            )

    def test_activate_already_active_raises(self):

        gate = GateService.create(
            township=self.township,
            name="درب",
            code="G-1",
        )

        with self.assertRaises(ValidationError):

            GateService.activate(gate)

    def test_deactivate_then_activate(self):

        gate = GateService.create(
            township=self.township,
            name="درب",
            code="G-1",
        )

        GateService.deactivate(gate)

        gate.refresh_from_db()

        self.assertFalse(gate.is_active)

        GateService.activate(gate)

        gate.refresh_from_db()

        self.assertTrue(gate.is_active)

    def test_deactivate_already_inactive_raises(self):

        gate = GateService.create(
            township=self.township,
            name="درب",
            code="G-1",
            is_active=False,
        )

        with self.assertRaises(ValidationError):

            GateService.deactivate(gate)

    def test_update_rejects_unknown_field(self):

        gate = GateService.create(
            township=self.township,
            name="درب",
            code="G-1",
        )

        with self.assertRaises(ValidationError):

            GateService.update(
                gate=gate,
                township=self.township,
            )

    def test_update_changes_allowed_fields(self):

        gate = GateService.create(
            township=self.township,
            name="درب",
            code="G-1",
        )

        GateService.update(
            gate=gate,
            name="درب جدید",
        )

        gate.refresh_from_db()

        self.assertEqual(gate.name, "درب جدید")

    def test_deactivate_all_for_township(self):

        GateService.create(
            township=self.township,
            name="درب ۱",
            code="G-1",
        )

        GateService.create(
            township=self.township,
            name="درب ۲",
            code="G-2",
        )

        updated = GateService.deactivate_all_for_township(
            self.township,
        )

        self.assertEqual(updated, 2)

        self.assertEqual(
            Gate.objects.filter(
                township=self.township,
                is_active=True,
            ).count(),
            0,
        )
