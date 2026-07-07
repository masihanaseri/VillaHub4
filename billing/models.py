"""
Billing module models.

Cross-app relations use lazy string references:

    villas.Residence       -> the resident/unit-occupancy record
    townships.Township     -> the township
    accounts.User          -> settings.AUTH_USER_MODEL
"""
import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

from billing.managers import (
    InvoiceQuerySet,
    PaymentQuerySet,
    BillingCycleQuerySet,
)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------
class TimeStampedUUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# 1. Charge Types
# ---------------------------------------------------------------------------
class ChargeType(TimeStampedUUIDModel):
    """Administrator-defined billable concept (Monthly Charge, Repair, ...)."""

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Charge Type"
        verbose_name_plural = "Charge Types"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify

            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# 2. Charge Rules (extensible calculation strategies)
# ---------------------------------------------------------------------------
class CalculationMethod(models.TextChoices):
    FIXED_AMOUNT = "fixed_amount", "Fixed Amount"
    PER_SQUARE_METER = "per_square_meter", "Per Square Meter"
    PER_RESIDENCE = "per_residence", "Per Residence"
    PER_PERSON = "per_person", "Per Person"
    BY_VILLA_TYPE = "by_villa_type", "By Villa Type"
    BY_BLOCK = "by_block", "By Block"
    FORMULA_BASED = "formula_based", "Formula Based"


class ChargeRule(TimeStampedUUIDModel):
    """
    Defines HOW a ChargeType's amount is computed. New calculation
    methods can be added to CalculationMethod and handled by adding a
    `_calculate_<method>` branch in services.ChargeCalculationService
    without touching this model.
    """

    charge_type = models.ForeignKey(
        ChargeType, on_delete=models.PROTECT, related_name="rules"
    )
    name = models.CharField(max_length=150)
    calculation_method = models.CharField(
        max_length=32, choices=CalculationMethod.choices
    )

    # Generic numeric inputs reused across methods depending on
    # calculation_method - kept simple/flat rather than one table per
    # method, per Clean Architecture "extensible, not exploding schema".
    base_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        help_text="Used by FIXED_AMOUNT, PER_RESIDENCE, PER_PERSON, BY_BLOCK.",
    )
    rate_per_unit = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Used by PER_SQUARE_METER (rate per m²).",
    )
    villa_type = models.CharField(
        max_length=100, blank=True,
        help_text="Free-text match against villas app villa type; "
                   "replace with a real FK once villas.VillaType is confirmed.",
    )
    block = models.CharField(max_length=100, blank=True)
    formula = models.TextField(
        blank=True,
        help_text="Whitelisted arithmetic expression evaluated by "
                   "services.FormulaEvaluator, e.g. 'area * 1.5 + 20'.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["charge_type__name", "name"]
        verbose_name = "Charge Rule"
        verbose_name_plural = "Charge Rules"

    def __str__(self):
        return f"{self.charge_type.name} / {self.name}"


# ---------------------------------------------------------------------------
# 3. Billing Cycle
# ---------------------------------------------------------------------------
class BillingFrequency(models.TextChoices):
    MONTHLY = "monthly", "Monthly"
    QUARTERLY = "quarterly", "Quarterly"
    YEARLY = "yearly", "Yearly"
    CUSTOM = "custom", "Custom"


class BillingCycle(TimeStampedUUIDModel):
    """A recurring schedule that turns a ChargeRule into Invoices."""

    name = models.CharField(max_length=150)
    charge_rule = models.ForeignKey(
        ChargeRule, on_delete=models.CASCADE, related_name="billing_cycles"
    )
    frequency = models.CharField(max_length=16, choices=BillingFrequency.choices)
    custom_interval_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Required only when frequency=CUSTOM.",
    )
    start_date = models.DateField()
    next_run_date = models.DateField()
    due_in_days = models.PositiveIntegerField(
        default=14, help_text="Days after issue_date the invoice is due."
    )
    auto_generate = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    objects = BillingCycleQuerySet.as_manager()

    class Meta:
        ordering = ["next_run_date"]
        verbose_name = "Billing Cycle"
        verbose_name_plural = "Billing Cycles"

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"

    def interval(self) -> timedelta:
        return {
            BillingFrequency.MONTHLY: timedelta(days=30),
            BillingFrequency.QUARTERLY: timedelta(days=91),
            BillingFrequency.YEARLY: timedelta(days=365),
        }.get(self.frequency, timedelta(days=self.custom_interval_days or 30))


# ---------------------------------------------------------------------------
# 4. Invoice
# ---------------------------------------------------------------------------
class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ISSUED = "issued", "Issued"
    PARTIALLY_PAID = "partially_paid", "Partially Paid"
    PAID = "paid", "Paid"
    OVERDUE = "overdue", "Overdue"
    CANCELLED = "cancelled", "Cancelled"


class Invoice(TimeStampedUUIDModel):
    invoice_number = models.CharField(max_length=32, unique=True, editable=False)

    # See module docstring: adjust `to=` if real app/model names differ.
    residence = models.ForeignKey(
        "villas.Residence", on_delete=models.PROTECT, related_name="invoices"
    )
    township = models.ForeignKey(
        "townships.Township", on_delete=models.PROTECT, related_name="invoices"
    )

    billing_cycle = models.ForeignKey(
        BillingCycle, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="invoices",
    )

    issue_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT
    )

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    discount_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    penalty_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    remaining_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="invoices_created",
    )

    objects = InvoiceQuerySet.as_manager()

    class Meta:
        ordering = ["-issue_date", "-created_at"]
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["residence", "status"]),
        ]

    def __str__(self):
        return self.invoice_number

    # Totals are always recomputed by services.InvoiceService, never by
    # ad-hoc view/serializer code. See services.InvoiceService.recalculate_totals.
    def is_overdue(self) -> bool:
        return (
            self.status in (InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID)
            and self.due_date < timezone.localdate()
        )


# ---------------------------------------------------------------------------
# 5. Invoice Items
# ---------------------------------------------------------------------------
class InvoiceItem(TimeStampedUUIDModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    charge_type = models.ForeignKey(
        ChargeType, on_delete=models.PROTECT, related_name="invoice_items"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=14, decimal_places=2, editable=False)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Invoice Item"
        verbose_name_plural = "Invoice Items"

    def __str__(self):
        return f"{self.title} x{self.quantity}"

    def save(self, *args, **kwargs):
        self.amount = (self.quantity * self.unit_price).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# 6. Discounts
# ---------------------------------------------------------------------------
class DiscountType(models.TextChoices):
    PERCENTAGE = "percentage", "Percentage"
    FIXED_AMOUNT = "fixed_amount", "Fixed Amount"
    EARLY_PAYMENT = "early_payment", "Early Payment"
    CUSTOM = "custom", "Custom"


class Discount(TimeStampedUUIDModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="discounts")
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    value = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Percentage points (0-100) if type=PERCENTAGE, otherwise a currency amount.",
    )
    reason = models.CharField(max_length=255, blank=True)
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Discount"
        verbose_name_plural = "Discounts"

    def __str__(self):
        return f"{self.get_discount_type_display()} on {self.invoice.invoice_number}"


# ---------------------------------------------------------------------------
# 7. Penalties
# ---------------------------------------------------------------------------
class PenaltyType(models.TextChoices):
    PERCENTAGE = "percentage", "Percentage"
    DAILY = "daily", "Daily"
    MONTHLY = "monthly", "Monthly"
    FIXED = "fixed", "Fixed"


class Penalty(TimeStampedUUIDModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="penalties")
    penalty_type = models.CharField(max_length=20, choices=PenaltyType.choices)
    value = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Percentage points, daily/monthly rate, or fixed currency amount.",
    )
    reason = models.CharField(max_length=255, blank=True)
    is_automatic = models.BooleanField(default=False)
    applied_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-applied_at"]
        verbose_name = "Penalty"
        verbose_name_plural = "Penalties"

    def __str__(self):
        return f"{self.get_penalty_type_display()} on {self.invoice.invoice_number}"


# ---------------------------------------------------------------------------
# 8. Payments
# ---------------------------------------------------------------------------
class PaymentMethod(models.TextChoices):
    ONLINE = "online", "Online Payment"
    CARD_TO_CARD = "card_to_card", "Card To Card"
    CASH = "cash", "Cash"
    POS = "pos", "POS"
    BANK_TRANSFER = "bank_transfer", "Bank Transfer"
    MANUAL = "manual", "Manual"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"


class Payment(TimeStampedUUIDModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    reference_number = models.CharField(max_length=100, blank=True)
    tracking_code = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="payments_created",
    )
    status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )

    # Reserved for future payment-gateway integration (NOT implemented here,
    # per spec). Kept nullable/blank so no gateway coupling exists yet.
    gateway_name = models.CharField(max_length=50, blank=True)
    gateway_payload = models.JSONField(null=True, blank=True)

    objects = PaymentQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.amount} via {self.get_method_display()} ({self.status})"


# ---------------------------------------------------------------------------
# 9. Receipts
# ---------------------------------------------------------------------------
class Receipt(TimeStampedUUIDModel):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="receipt")
    receipt_number = models.CharField(max_length=32, unique=True, editable=False)
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to="billing/receipts/%Y/%m/", null=True, blank=True)

    class Meta:
        ordering = ["-issued_at"]
        verbose_name = "Receipt"
        verbose_name_plural = "Receipts"

    def __str__(self):
        return self.receipt_number
