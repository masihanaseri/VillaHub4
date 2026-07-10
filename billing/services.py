"""
Billing service layer.

Every business rule lives here. Models stay dumb (persistence +
simple derived fields), views/serializers stay dumb (I/O + shape),
and everything in between - calculations, state transitions,
cross-app notification, number generation - is a service function or
class method in this module.

Services are plain classes with @classmethod/@staticmethod so they're
trivially callable from views, management commands, Celery tasks and
the Django shell alike, and trivially unit-testable without HTTP.
"""
import ast
import operator
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum, Count, Value
from django.db.models.functions import Coalesce, TruncMonth, TruncYear
from django.utils import timezone

from billing.models import (
    ChargeRule,
    CalculationMethod,
    BillingCycle,
    Invoice,
    InvoiceStatus,
    InvoiceItem,
    Discount,
    DiscountType,
    Penalty,
    PenaltyType,
    Payment,
    PaymentStatus,
    Receipt,
)

TWO_PLACES = Decimal("0.01")


def _q(value) -> Decimal:
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Number generation
# ---------------------------------------------------------------------------
class NumberGenerator:
    """
    Sequential, year-scoped human-readable numbers, e.g. INV-2026-000123.
    Uses select_for_update inside a transaction to stay race-safe under
    concurrent invoice/receipt creation without needing a DB sequence.
    """

    @staticmethod
    @transaction.atomic
    def next_invoice_number() -> str:
        year = timezone.localdate().year
        prefix = f"INV-{year}-"
        last = (
            Invoice.objects.select_for_update()
            .filter(invoice_number__startswith=prefix)
            .order_by("-invoice_number")
            .first()
        )
        next_seq = int(last.invoice_number.split("-")[-1]) + 1 if last else 1
        return f"{prefix}{next_seq:06d}"

    @staticmethod
    @transaction.atomic
    def next_receipt_number() -> str:
        year = timezone.localdate().year
        prefix = f"RCT-{year}-"
        last = (
            Receipt.objects.select_for_update()
            .filter(receipt_number__startswith=prefix)
            .order_by("-receipt_number")
            .first()
        )
        next_seq = int(last.receipt_number.split("-")[-1]) + 1 if last else 1
        return f"{prefix}{next_seq:06d}"


# ---------------------------------------------------------------------------
# Formula evaluation (Formula Based charge rule)
# ---------------------------------------------------------------------------
class FormulaEvaluationError(Exception):
    pass


class FormulaEvaluator:
    """
    Evaluates a whitelisted arithmetic expression using variables
    `area`, `persons`, `units`, `base`. Uses the `ast` module - never
    Python's `eval()` - so arbitrary code execution is impossible.
    """

    _ALLOWED_BIN_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }
    _ALLOWED_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}

    @classmethod
    def evaluate(cls, expression: str, variables: dict) -> Decimal:
        try:
            tree = ast.parse(expression, mode="eval")
            result = cls._eval_node(tree.body, variables)
        except (SyntaxError, TypeError, ZeroDivisionError, KeyError) as exc:
            raise FormulaEvaluationError(f"Invalid formula '{expression}': {exc}")
        return _q(result)

    @classmethod
    def _eval_node(cls, node, variables):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return Decimal(str(node.value))
        if isinstance(node, ast.Name):
            if node.id not in variables:
                raise FormulaEvaluationError(f"Unknown variable '{node.id}'")
            return Decimal(str(variables[node.id] or 0))
        if isinstance(node, ast.BinOp) and type(node.op) in cls._ALLOWED_BIN_OPS:
            left = cls._eval_node(node.left, variables)
            right = cls._eval_node(node.right, variables)
            return cls._ALLOWED_BIN_OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in cls._ALLOWED_UNARY_OPS:
            return cls._ALLOWED_UNARY_OPS[type(node.op)](cls._eval_node(node.operand, variables))
        raise FormulaEvaluationError("Disallowed expression element.")


# ---------------------------------------------------------------------------
# Charge calculation strategy
# ---------------------------------------------------------------------------
class ChargeCalculationService:
    """
    Turns a ChargeRule + contextual inputs into a Decimal amount.
    Adding a new CalculationMethod only requires adding a branch here
    (and to CalculationMethod choices) - no model migration needed for
    the calculation logic itself.
    """

    @classmethod
    def calculate(cls, charge_rule: ChargeRule, *, area=None, persons=None,
                   residence_count=1, villa_type=None, block=None) -> Decimal:
        method = charge_rule.calculation_method

        if method == CalculationMethod.FIXED_AMOUNT:
            return _q(charge_rule.base_amount)

        if method == CalculationMethod.PER_SQUARE_METER:
            if area is None:
                raise ValueError("area is required for PER_SQUARE_METER rules.")
            rate = charge_rule.rate_per_unit or Decimal("0.00")
            return _q(Decimal(area) * rate)

        if method == CalculationMethod.PER_RESIDENCE:
            return _q(charge_rule.base_amount * residence_count)

        if method == CalculationMethod.PER_PERSON:
            if persons is None:
                raise ValueError("persons is required for PER_PERSON rules.")
            rate = charge_rule.rate_per_unit or charge_rule.base_amount
            return _q(rate * persons)

        if method == CalculationMethod.BY_VILLA_TYPE:
            if villa_type and charge_rule.villa_type and villa_type != charge_rule.villa_type:
                return Decimal("0.00")
            return _q(charge_rule.base_amount)

        if method == CalculationMethod.BY_BLOCK:
            if block and charge_rule.block and block != charge_rule.block:
                return Decimal("0.00")
            return _q(charge_rule.base_amount)

        if method == CalculationMethod.FORMULA_BASED:
            return FormulaEvaluator.evaluate(
                charge_rule.formula,
                {
                    "area": area or 0,
                    "persons": persons or 0,
                    "units": residence_count or 0,
                    "base": charge_rule.base_amount,
                },
            )

        raise ValueError(f"Unsupported calculation method: {method}")


# ---------------------------------------------------------------------------
# Notification bridge
# ---------------------------------------------------------------------------
class NotificationDispatcher:
    """
    Thin bridge to the existing `notifications` app. Billing never
    imports notifications models directly at module scope (keeps the
    two apps decoupled and avoids a hard dependency at migration time);
    it resolves the notification API lazily and fails soft (logs, does
    not raise) so a notifications outage never blocks billing.
    """

    EVENT_INVOICE_CREATED = "billing.invoice_created"
    EVENT_PAYMENT_SUCCESS = "billing.payment_success"
    EVENT_INVOICE_OVERDUE = "billing.invoice_overdue"
    EVENT_PENALTY_ADDED = "billing.penalty_added"

    @classmethod
    def _send(cls, event: str, *, recipient, title: str, message: str, notification_type: str):
        import logging

        logger = logging.getLogger("billing.notifications")
        if recipient is None:
            logger.info("no recipient resolved; skipped %s", event)
            return
        try:
            from django.apps import apps

            if not apps.is_installed("notifications"):
                logger.info("notifications app not installed; skipped %s", event)
                return
            from notifications.services import NotificationService  # noqa

            NotificationService.send(
                recipient=recipient,
                title=title,
                message=message,
                notification_type=notification_type,
            )
        except Exception:  # noqa: BLE001 - notification failures must never break billing
            logger.exception("Failed to dispatch notification event=%s", event)

    @classmethod
    def invoice_created(cls, invoice: Invoice):
        cls._send(
            cls.EVENT_INVOICE_CREATED,
            recipient=getattr(invoice.residence, "user", None),
            title="صورتحساب جدید",
            message=f"صورتحساب {invoice.invoice_number} به مبلغ {invoice.total} صادر شد. سررسید: {invoice.due_date.isoformat()}",
            notification_type="CHARGE",
        )

    @classmethod
    def payment_success(cls, payment: Payment):
        cls._send(
            cls.EVENT_PAYMENT_SUCCESS,
            recipient=getattr(payment.invoice.residence, "user", None),
            title="پرداخت موفق",
            message=f"پرداخت شما به مبلغ {payment.amount} برای صورتحساب {payment.invoice.invoice_number} با موفقیت ثبت شد.",
            notification_type="PAYMENT",
        )

    @classmethod
    def invoice_overdue(cls, invoice: Invoice):
        cls._send(
            cls.EVENT_INVOICE_OVERDUE,
            recipient=getattr(invoice.residence, "user", None),
            title="صورتحساب معوق",
            message=f"صورتحساب {invoice.invoice_number} معوق شده است. مبلغ باقیمانده: {invoice.remaining_amount}",
            notification_type="CHARGE",
        )

    @classmethod
    def penalty_added(cls, penalty: Penalty):
        cls._send(
            cls.EVENT_PENALTY_ADDED,
            recipient=getattr(penalty.invoice.residence, "user", None),
            title="جریمه تأخیر",
            message=f"جریمه‌ای به مبلغ {penalty.value} به صورتحساب {penalty.invoice.invoice_number} اضافه شد.",
            notification_type="CHARGE",
        )


# ---------------------------------------------------------------------------
# Invoice service
# ---------------------------------------------------------------------------
class InvoiceService:
    @staticmethod
    @transaction.atomic
    def create_invoice(*, residence, township, due_date=None, billing_cycle=None,
                        notes="", created_by=None, items: list[dict] | None = None) -> Invoice:
        issue_date = timezone.localdate()
        due_date = due_date or (issue_date + timedelta(days=14))

        invoice = Invoice.objects.create(
            invoice_number=NumberGenerator.next_invoice_number(),
            residence=residence,
            township=township,
            billing_cycle=billing_cycle,
            issue_date=issue_date,
            due_date=due_date,
            status=InvoiceStatus.DRAFT,
            notes=notes,
            created_by=created_by,
        )

        for item in items or []:
            InvoiceService.add_item(invoice, **item)

        InvoiceService.recalculate_totals(invoice)
        return invoice

    @staticmethod
    def add_item(invoice: Invoice, *, charge_type, title, unit_price,
                  quantity=Decimal("1.00"), description="") -> InvoiceItem:
        item = InvoiceItem.objects.create(
            invoice=invoice,
            charge_type=charge_type,
            title=title,
            description=description,
            quantity=quantity,
            unit_price=unit_price,
        )
        InvoiceService.recalculate_totals(invoice)
        return item

    @staticmethod
    def remove_item(invoice: Invoice, item_id):
        InvoiceItem.objects.filter(invoice=invoice, id=item_id).delete()
        InvoiceService.recalculate_totals(invoice)

    @staticmethod
    def apply_discount(invoice: Invoice, *, discount_type, value, reason="",
                        applied_by=None) -> Discount:
        discount = Discount.objects.create(
            invoice=invoice,
            discount_type=discount_type,
            value=value,
            reason=reason,
            applied_by=applied_by,
        )
        InvoiceService.recalculate_totals(invoice)
        return discount

    @staticmethod
    def apply_penalty(invoice: Invoice, *, penalty_type, value, reason="",
                       is_automatic=False) -> Penalty:
        penalty = Penalty.objects.create(
            invoice=invoice,
            penalty_type=penalty_type,
            value=value,
            reason=reason,
            is_automatic=is_automatic,
        )
        InvoiceService.recalculate_totals(invoice)
        NotificationDispatcher.penalty_added(penalty)
        return penalty

    @staticmethod
    def _calculate_discount_total(invoice: Invoice, subtotal: Decimal) -> Decimal:
        total = Decimal("0.00")
        for discount in invoice.discounts.all():
            if discount.discount_type == DiscountType.PERCENTAGE:
                total += subtotal * (discount.value / Decimal("100"))
            else:  # FIXED_AMOUNT, EARLY_PAYMENT, CUSTOM all carry a currency value
                total += discount.value
        return _q(min(total, subtotal))

    @staticmethod
    def _calculate_penalty_total(invoice: Invoice, subtotal: Decimal) -> Decimal:
        total = Decimal("0.00")
        days_overdue = max((timezone.localdate() - invoice.due_date).days, 0)
        for penalty in invoice.penalties.all():
            if penalty.penalty_type == PenaltyType.PERCENTAGE:
                total += subtotal * (penalty.value / Decimal("100"))
            elif penalty.penalty_type == PenaltyType.DAILY:
                total += penalty.value * days_overdue
            elif penalty.penalty_type == PenaltyType.MONTHLY:
                total += penalty.value * (days_overdue // 30)
            else:  # FIXED
                total += penalty.value
        return _q(total)

    @staticmethod
    @transaction.atomic
    def recalculate_totals(invoice: Invoice) -> Invoice:
        subtotal = invoice.items.aggregate(
            s=Coalesce(Sum("amount"), Value(Decimal("0.00")))
        )["s"]

        discount_total = InvoiceService._calculate_discount_total(invoice, subtotal)
        penalty_total = InvoiceService._calculate_penalty_total(invoice, subtotal)
        total = _q(subtotal - discount_total + penalty_total)

        paid_amount = invoice.payments.filter(status=PaymentStatus.SUCCESS).aggregate(
            s=Coalesce(Sum("amount"), Value(Decimal("0.00")))
        )["s"]
        remaining_amount = _q(max(total - paid_amount, Decimal("0.00")))

        invoice.subtotal = _q(subtotal)
        invoice.discount_total = discount_total
        invoice.penalty_total = penalty_total
        invoice.total = total
        invoice.paid_amount = _q(paid_amount)
        invoice.remaining_amount = remaining_amount

        if invoice.status not in (InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED):
            if remaining_amount <= Decimal("0.00"):
                invoice.status = InvoiceStatus.PAID
            elif paid_amount > Decimal("0.00"):
                invoice.status = InvoiceStatus.PARTIALLY_PAID
            elif invoice.is_overdue():
                invoice.status = InvoiceStatus.OVERDUE
            else:
                invoice.status = InvoiceStatus.ISSUED

        invoice.save(update_fields=[
            "subtotal", "discount_total", "penalty_total", "total",
            "paid_amount", "remaining_amount", "status", "updated_at",
        ])
        return invoice

    @staticmethod
    @transaction.atomic
    def issue(invoice: Invoice) -> Invoice:
        if invoice.status != InvoiceStatus.DRAFT:
            raise ValueError("Only draft invoices can be issued.")
        invoice.status = InvoiceStatus.ISSUED
        invoice.save(update_fields=["status", "updated_at"])
        InvoiceService.recalculate_totals(invoice)
        NotificationDispatcher.invoice_created(invoice)
        return invoice

    @staticmethod
    @transaction.atomic
    def cancel(invoice: Invoice) -> Invoice:
        if invoice.status == InvoiceStatus.PAID:
            raise ValueError("Paid invoices cannot be cancelled.")
        invoice.status = InvoiceStatus.CANCELLED
        invoice.save(update_fields=["status", "updated_at"])
        return invoice

    @staticmethod
    def mark_overdue_if_needed(invoice: Invoice) -> Invoice:
        if invoice.is_overdue() and invoice.status != InvoiceStatus.OVERDUE:
            invoice.status = InvoiceStatus.OVERDUE
            invoice.save(update_fields=["status", "updated_at"])
            NotificationDispatcher.invoice_overdue(invoice)
        return invoice


# ---------------------------------------------------------------------------
# Billing cycle / automatic generation service
# ---------------------------------------------------------------------------
class BillingCycleService:
    @staticmethod
    @transaction.atomic
    def generate_invoice_for_residence(cycle: BillingCycle, residence, township, *,
                                        area=None, persons=None, villa_type=None,
                                        block=None) -> Invoice:
        rule = cycle.charge_rule
        amount = ChargeCalculationService.calculate(
            rule, area=area, persons=persons, villa_type=villa_type, block=block,
        )
        issue_date = timezone.localdate()
        invoice = InvoiceService.create_invoice(
            residence=residence,
            township=township,
            due_date=issue_date + timedelta(days=cycle.due_in_days),
            billing_cycle=cycle,
            notes=f"Auto-generated by billing cycle '{cycle.name}'.",
            items=[{
                "charge_type": rule.charge_type,
                "title": rule.charge_type.name,
                "unit_price": amount,
                "quantity": Decimal("1.00"),
            }],
        )
        return InvoiceService.issue(invoice)

    @staticmethod
    def advance_next_run_date(cycle: BillingCycle):
        cycle.next_run_date = cycle.next_run_date + cycle.interval()
        cycle.save(update_fields=["next_run_date", "updated_at"])

    @staticmethod
    def run_due_cycles(residence_provider) -> int:
        """
        residence_provider: callable(township) -> iterable of
        (residence, township, context_dict) tuples. Injected rather than
        imported directly, since this module has no confirmed access to
        the real `residences`/`townships` querysets.
        """
        generated = 0
        for cycle in BillingCycle.objects.due_for_generation():
            for residence, township, context in residence_provider(cycle):
                BillingCycleService.generate_invoice_for_residence(
                    cycle, residence, township, **context
                )
                generated += 1
            BillingCycleService.advance_next_run_date(cycle)
        return generated


# ---------------------------------------------------------------------------
# Payment service
# ---------------------------------------------------------------------------
class PaymentService:
    @staticmethod
    @transaction.atomic
    def record_payment(*, invoice: Invoice, amount, method, reference_number="",
                        tracking_code="", created_by=None,
                        status=PaymentStatus.PENDING) -> Payment:
        from billing.validators import validate_payment_amount_within_remaining

        if status == PaymentStatus.SUCCESS:
            validate_payment_amount_within_remaining(amount, invoice.remaining_amount)

        payment = Payment.objects.create(
            invoice=invoice,
            amount=amount,
            method=method,
            reference_number=reference_number,
            tracking_code=tracking_code,
            created_by=created_by,
            status=status,
            paid_at=timezone.now() if status == PaymentStatus.SUCCESS else None,
        )
        if status == PaymentStatus.SUCCESS:
            PaymentService._on_success(payment)
        return payment

    @staticmethod
    @transaction.atomic
    def mark_success(payment: Payment) -> Payment:
        if payment.status == PaymentStatus.SUCCESS:
            return payment
        payment.status = PaymentStatus.SUCCESS
        payment.paid_at = payment.paid_at or timezone.now()
        payment.save(update_fields=["status", "paid_at", "updated_at"])
        PaymentService._on_success(payment)
        return payment

    @staticmethod
    def _on_success(payment: Payment):
        InvoiceService.recalculate_totals(payment.invoice)
        ReceiptService.generate_receipt(payment)
        NotificationDispatcher.payment_success(payment)

    @staticmethod
    @transaction.atomic
    def mark_failed(payment: Payment, reason: str = "") -> Payment:
        payment.status = PaymentStatus.FAILED
        payment.gateway_payload = {**(payment.gateway_payload or {}), "failure_reason": reason}
        payment.save(update_fields=["status", "gateway_payload", "updated_at"])
        return payment

    @staticmethod
    @transaction.atomic
    def refund(payment: Payment) -> Payment:
        if payment.status != PaymentStatus.SUCCESS:
            raise ValueError("Only successful payments can be refunded.")
        payment.status = PaymentStatus.REFUNDED
        payment.save(update_fields=["status", "updated_at"])
        InvoiceService.recalculate_totals(payment.invoice)
        return payment


# ---------------------------------------------------------------------------
# Receipt service
# ---------------------------------------------------------------------------
class ReceiptService:
    @staticmethod
    def generate_receipt(payment: Payment) -> Receipt:
        receipt, _ = Receipt.objects.get_or_create(
            payment=payment,
            defaults={"receipt_number": NumberGenerator.next_receipt_number()},
        )
        return receipt

    @staticmethod
    def render_pdf(receipt: Receipt):

        raise NotImplementedError(
            "PDF rendering is not implemented yet - hook a PDF engine "
            "here and populate receipt.pdf_file."
        )


# ---------------------------------------------------------------------------
# Finance report service (read-only, AI-ready aggregate queries)
# ---------------------------------------------------------------------------
class ReportService:

    @staticmethod
    def total_income(start_date, end_date) -> Decimal:
        return Payment.objects.successful().in_period(start_date, end_date).aggregate(
            s=Coalesce(Sum("amount"), Value(Decimal("0.00")))
        )["s"]

    @staticmethod
    def outstanding_debts(township_id=None):
        qs = Invoice.objects.unpaid()
        if township_id:
            qs = qs.filter(township_id=township_id)
        return qs.aggregate(s=Coalesce(Sum("remaining_amount"), Value(Decimal("0.00"))))["s"]

    @staticmethod
    def collected_charges(start_date, end_date, by_charge_type=True):
        qs = InvoiceItem.objects.filter(
            invoice__payments__status=PaymentStatus.SUCCESS,
            invoice__payments__paid_at__date__gte=start_date,
            invoice__payments__paid_at__date__lte=end_date,
        )
        if by_charge_type:
            return qs.values("charge_type__name").annotate(total=Sum("amount")).order_by("-total")
        return qs.aggregate(total=Coalesce(Sum("amount"), Value(Decimal("0.00"))))["total"]

    @staticmethod
    def top_debtors(limit=10):
        return (
            Invoice.objects.unpaid()
            .values("residence_id")
            .annotate(total_owed=Sum("remaining_amount"), invoice_count=Count("id"))
            .order_by("-total_owed")[:limit]
        )

    @staticmethod
    def collection_rate(start_date, end_date) -> Decimal:
        invoiced = Invoice.objects.in_period(start_date, end_date).aggregate(
            s=Coalesce(Sum("total"), Value(Decimal("0.00")))
        )["s"]
        collected = ReportService.total_income(start_date, end_date)
        if invoiced == 0:
            return Decimal("0.00")
        return _q((collected / invoiced) * Decimal("100"))

    @staticmethod
    def penalty_report(start_date, end_date):
        return Penalty.objects.filter(
            applied_at__date__gte=start_date, applied_at__date__lte=end_date
        ).values("penalty_type").annotate(total=Sum("value"), count=Count("id"))

    @staticmethod
    def monthly_report(year: int):
        return (
            Invoice.objects.filter(issue_date__year=year)
            .annotate(month=TruncMonth("issue_date"))
            .values("month")
            .annotate(invoiced=Sum("total"), collected=Sum("paid_amount"))
            .order_by("month")
        )

    @staticmethod
    def yearly_report():
        return (
            Invoice.objects.annotate(year=TruncYear("issue_date"))
            .values("year")
            .annotate(invoiced=Sum("total"), collected=Sum("paid_amount"))
            .order_by("year")
        )
