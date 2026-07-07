from decimal import Decimal

from django.test import TestCase

from billing.models import InvoiceStatus
from billing.tests.factories import (
    ChargeTypeFactory,
    ChargeRuleFactory,
    InvoiceFactory,
)


class ChargeTypeModelTests(TestCase):
    def test_slug_is_auto_generated_from_name(self):
        charge_type = ChargeTypeFactory(name="Swimming Pool")
        self.assertEqual(charge_type.slug, "swimming-pool")

    def test_str_returns_name(self):
        charge_type = ChargeTypeFactory(name="Gym")
        self.assertEqual(str(charge_type), "Gym")


class ChargeRuleModelTests(TestCase):
    def test_str_includes_charge_type_and_rule_name(self):
        rule = ChargeRuleFactory(name="Standard Fixed")
        self.assertIn(rule.charge_type.name, str(rule))
        self.assertIn("Standard Fixed", str(rule))


class InvoiceModelTests(TestCase):
    def test_is_overdue_false_for_draft(self):
        from datetime import timedelta

        from django.utils import timezone

        invoice = InvoiceFactory(
            status=InvoiceStatus.DRAFT,
            due_date=timezone.localdate() - timedelta(days=5),
        )
        self.assertFalse(invoice.is_overdue())

    def test_is_overdue_true_for_issued_past_due_date(self):
        from datetime import timedelta

        from django.utils import timezone

        invoice = InvoiceFactory(
            status=InvoiceStatus.ISSUED,
            due_date=timezone.localdate() - timedelta(days=1),
        )
        self.assertTrue(invoice.is_overdue())

    def test_invoice_item_amount_is_computed_on_save(self):
        invoice = InvoiceFactory()
        charge_type = ChargeTypeFactory()
        item = invoice.items.create(
            charge_type=charge_type,
            title="Maintenance",
            quantity=Decimal("2.00"),
            unit_price=Decimal("50.00"),
        )
        self.assertEqual(item.amount, Decimal("100.00"))
