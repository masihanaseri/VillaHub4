from decimal import Decimal

from django.test import TestCase

from billing.models import InvoiceStatus, PaymentStatus, CalculationMethod
from billing.services import (
    ChargeCalculationService,
    FormulaEvaluator,
    FormulaEvaluationError,
    InvoiceService,
    PaymentService,
    ReceiptService,
    ReportService,
)
from billing.tests.factories import (
    ChargeTypeFactory,
    ChargeRuleFactory,
    InvoiceFactory,
    get_or_create_test_residence,
    get_or_create_test_township,
)


class FormulaEvaluatorTests(TestCase):
    def test_evaluates_basic_arithmetic(self):
        result = FormulaEvaluator.evaluate("area * 2 + 10", {"area": 50})
        self.assertEqual(result, Decimal("110.00"))

    def test_rejects_unknown_variable(self):
        with self.assertRaises(FormulaEvaluationError):
            FormulaEvaluator.evaluate("__import__('os')", {"area": 1})

    def test_rejects_disallowed_call_expression(self):
        with self.assertRaises(FormulaEvaluationError):
            FormulaEvaluator.evaluate("area()", {"area": 1})


class ChargeCalculationServiceTests(TestCase):
    def test_fixed_amount(self):
        rule = ChargeRuleFactory(
            calculation_method=CalculationMethod.FIXED_AMOUNT, base_amount=Decimal("200.00")
        )
        self.assertEqual(ChargeCalculationService.calculate(rule), Decimal("200.00"))

    def test_per_square_meter(self):
        rule = ChargeRuleFactory(
            calculation_method=CalculationMethod.PER_SQUARE_METER,
            rate_per_unit=Decimal("3.50"),
        )
        self.assertEqual(
            ChargeCalculationService.calculate(rule, area=100), Decimal("350.00")
        )

    def test_per_square_meter_requires_area(self):
        rule = ChargeRuleFactory(calculation_method=CalculationMethod.PER_SQUARE_METER)
        with self.assertRaises(ValueError):
            ChargeCalculationService.calculate(rule)

    def test_formula_based(self):
        rule = ChargeRuleFactory(
            calculation_method=CalculationMethod.FORMULA_BASED,
            formula="area * 1.5 + persons * 10",
        )
        result = ChargeCalculationService.calculate(rule, area=40, persons=3)
        self.assertEqual(result, Decimal("90.00"))


class InvoiceServiceTests(TestCase):
    def setUp(self):
        self.residence = get_or_create_test_residence()
        self.township = get_or_create_test_township()
        self.charge_type = ChargeTypeFactory()

    def test_create_invoice_with_items_computes_totals(self):
        invoice = InvoiceService.create_invoice(
            residence=self.residence,
            township=self.township,
            items=[
                {"charge_type": self.charge_type, "title": "Monthly Fee",
                 "unit_price": Decimal("100.00"), "quantity": Decimal("1.00")},
                {"charge_type": self.charge_type, "title": "Parking",
                 "unit_price": Decimal("50.00"), "quantity": Decimal("2.00")},
            ],
        )
        self.assertEqual(invoice.subtotal, Decimal("200.00"))
        self.assertEqual(invoice.total, Decimal("200.00"))
        self.assertEqual(invoice.status, InvoiceStatus.DRAFT)

    def test_apply_percentage_discount_reduces_total(self):
        invoice = InvoiceService.create_invoice(
            residence=self.residence, township=self.township,
            items=[{"charge_type": self.charge_type, "title": "Fee",
                    "unit_price": Decimal("100.00")}],
        )
        InvoiceService.apply_discount(invoice, discount_type="percentage", value=Decimal("10"))
        invoice.refresh_from_db()
        self.assertEqual(invoice.discount_total, Decimal("10.00"))
        self.assertEqual(invoice.total, Decimal("90.00"))

    def test_apply_fixed_penalty_increases_total(self):
        invoice = InvoiceService.create_invoice(
            residence=self.residence, township=self.township,
            items=[{"charge_type": self.charge_type, "title": "Fee",
                    "unit_price": Decimal("100.00")}],
        )
        InvoiceService.apply_penalty(invoice, penalty_type="fixed", value=Decimal("25.00"))
        invoice.refresh_from_db()
        self.assertEqual(invoice.penalty_total, Decimal("25.00"))
        self.assertEqual(invoice.total, Decimal("125.00"))

    def test_issue_moves_draft_to_issued(self):
        invoice = InvoiceFactory(residence=self.residence, township=self.township)
        invoice = InvoiceService.issue(invoice)
        self.assertEqual(invoice.status, InvoiceStatus.ISSUED)

    def test_issue_raises_for_non_draft_invoice(self):
        invoice = InvoiceFactory(
            residence=self.residence, township=self.township, status=InvoiceStatus.ISSUED
        )
        with self.assertRaises(ValueError):
            InvoiceService.issue(invoice)

    def test_cancel_paid_invoice_raises(self):
        invoice = InvoiceFactory(
            residence=self.residence, township=self.township, status=InvoiceStatus.PAID
        )
        with self.assertRaises(ValueError):
            InvoiceService.cancel(invoice)


class PaymentServiceTests(TestCase):
    def setUp(self):
        self.residence = get_or_create_test_residence()
        self.township = get_or_create_test_township()
        self.charge_type = ChargeTypeFactory()
        invoice = InvoiceService.create_invoice(
            residence=self.residence, township=self.township,
            items=[{"charge_type": self.charge_type, "title": "Fee",
                    "unit_price": Decimal("300.00")}],
        )
        self.invoice = InvoiceService.issue(invoice)

    def test_successful_payment_updates_invoice_balance(self):
        PaymentService.record_payment(
            invoice=self.invoice, amount=Decimal("300.00"), method="cash",
            status=PaymentStatus.SUCCESS,
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.remaining_amount, Decimal("0.00"))
        self.assertEqual(self.invoice.status, InvoiceStatus.PAID)

    def test_partial_payment_sets_partially_paid_status(self):
        PaymentService.record_payment(
            invoice=self.invoice, amount=Decimal("100.00"), method="cash",
            status=PaymentStatus.SUCCESS,
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, InvoiceStatus.PARTIALLY_PAID)
        self.assertEqual(self.invoice.remaining_amount, Decimal("200.00"))

    def test_payment_exceeding_remaining_amount_is_rejected(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            PaymentService.record_payment(
                invoice=self.invoice, amount=Decimal("999.00"), method="cash",
                status=PaymentStatus.SUCCESS,
            )

    def test_successful_payment_generates_receipt(self):
        payment = PaymentService.record_payment(
            invoice=self.invoice, amount=Decimal("300.00"), method="cash",
            status=PaymentStatus.SUCCESS,
        )
        self.assertTrue(hasattr(payment, "receipt"))

    def test_refund_reverts_invoice_balance(self):
        payment = PaymentService.record_payment(
            invoice=self.invoice, amount=Decimal("300.00"), method="cash",
            status=PaymentStatus.SUCCESS,
        )
        PaymentService.refund(payment)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.remaining_amount, Decimal("300.00"))


class ReportServiceTests(TestCase):
    def test_outstanding_debts_sums_unpaid_invoices(self):
        residence = get_or_create_test_residence()
        township = get_or_create_test_township()
        charge_type = ChargeTypeFactory()
        invoice = InvoiceService.create_invoice(
            residence=residence, township=township,
            items=[{"charge_type": charge_type, "title": "Fee", "unit_price": Decimal("80.00")}],
        )
        InvoiceService.issue(invoice)
        self.assertEqual(ReportService.outstanding_debts(), Decimal("80.00"))
