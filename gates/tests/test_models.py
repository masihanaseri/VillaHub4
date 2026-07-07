from django.db import IntegrityError

from django.test import TestCase

from townships.models import Township

from ..models import Gate


class GateModelTests(TestCase):

    def setUp(self):

        self.township = Township.objects.create(
            code="TS1",
            name="شهرک تست",
        )

    def test_str_representation(self):

        gate = Gate.objects.create(
            township=self.township,
            name="درب اصلی",
            code="gate-01",
        )

        self.assertIn("درب اصلی", str(gate))

        self.assertIn("GATE-01", str(gate))

    def test_code_is_normalized_to_uppercase(self):

        gate = Gate.objects.create(
            township=self.township,
            name="درب شرقی",
            code="east-gate",
        )

        self.assertEqual(gate.code, "EAST-GATE")

    def test_unique_code_per_township(self):

        Gate.objects.create(
            township=self.township,
            name="درب اول",
            code="G-1",
        )

        with self.assertRaises(IntegrityError):

            Gate.objects.create(
                township=self.township,
                name="درب دوم",
                code="G-1",
            )

    def test_same_code_allowed_in_different_township(self):

        other_township = Township.objects.create(
            code="TS2",
            name="شهرک دوم",
        )

        Gate.objects.create(
            township=self.township,
            name="درب اول",
            code="G-1",
        )

        gate = Gate.objects.create(
            township=other_township,
            name="درب اول",
            code="G-1",
        )

        self.assertEqual(gate.code, "G-1")

    def test_has_coordinates_property(self):

        gate_without = Gate.objects.create(
            township=self.township,
            name="درب بدون مختصات",
            code="G-2",
        )

        gate_with = Gate.objects.create(
            township=self.township,
            name="درب با مختصات",
            code="G-3",
            latitude="35.700000",
            longitude="51.400000",
        )

        self.assertFalse(gate_without.has_coordinates)

        self.assertTrue(gate_with.has_coordinates)

    def test_manager_active_and_inactive(self):

        Gate.objects.create(
            township=self.township,
            name="درب فعال",
            code="G-ACTIVE",
            is_active=True,
        )

        Gate.objects.create(
            township=self.township,
            name="درب غیرفعال",
            code="G-INACTIVE",
            is_active=False,
        )

        self.assertEqual(Gate.objects.active().count(), 1)

        self.assertEqual(Gate.objects.inactive().count(), 1)

    def test_lat_lng_must_be_provided_together(self):

        with self.assertRaises(IntegrityError):

            Gate.objects.create(
                township=self.township,
                name="درب ناقص",
                code="G-BAD",
                latitude="35.700000",
                longitude=None,
            )
