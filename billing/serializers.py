"""
DRF serializers. Pure I/O shaping and field-level validation only -
anything cross-field or stateful is delegated to billing.services.
"""
from rest_framework import serializers

from billing.models import (
    ChargeType,
    ChargeRule,
    BillingCycle,
    Invoice,
    InvoiceItem,
    Discount,
    Penalty,
    Payment,
    Receipt,
)
from billing.validators import validate_percentage, validate_positive_amount


class ChargeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChargeType
        fields = ["id", "name", "slug", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]


class ChargeRuleSerializer(serializers.ModelSerializer):
    charge_type_name = serializers.CharField(source="charge_type.name", read_only=True)

    class Meta:
        model = ChargeRule
        fields = [
            "id", "charge_type", "charge_type_name", "name", "calculation_method",
            "base_amount", "rate_per_unit", "villa_type", "block", "formula",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        method = attrs.get("calculation_method", getattr(self.instance, "calculation_method", None))
        if method == "formula_based" and not attrs.get("formula", getattr(self.instance, "formula", "")):
            raise serializers.ValidationError({"formula": "Required for FORMULA_BASED rules."})
        if method == "per_square_meter" and attrs.get("rate_per_unit") is None:
            existing = getattr(self.instance, "rate_per_unit", None)
            if existing is None:
                raise serializers.ValidationError(
                    {"rate_per_unit": "Required for PER_SQUARE_METER rules."}
                )
        return attrs


class BillingCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingCycle
        fields = [
            "id", "name", "charge_rule", "frequency", "custom_interval_days",
            "start_date", "next_run_date", "due_in_days", "auto_generate",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        frequency = attrs.get("frequency", getattr(self.instance, "frequency", None))
        interval = attrs.get(
            "custom_interval_days", getattr(self.instance, "custom_interval_days", None)
        )
        if frequency == "custom" and not interval:
            raise serializers.ValidationError(
                {"custom_interval_days": "Required when frequency=custom."}
            )
        return attrs


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = [
            "id", "invoice", "charge_type", "title", "description",
            "quantity", "unit_price", "amount", "created_at",
        ]
        read_only_fields = ["id", "amount", "created_at"]

    def validate_unit_price(self, value):
        validate_positive_amount(value)
        return value


class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = [
            "id", "invoice", "discount_type", "value", "reason",
            "applied_by", "created_at",
        ]
        read_only_fields = ["id", "applied_by", "created_at"]

    def validate(self, attrs):
        if attrs.get("discount_type") == "percentage":
            validate_percentage(attrs.get("value"))
        else:
            validate_positive_amount(attrs.get("value"))
        return attrs


class PenaltySerializer(serializers.ModelSerializer):
    class Meta:
        model = Penalty
        fields = [
            "id", "invoice", "penalty_type", "value", "reason",
            "is_automatic", "applied_at",
        ]
        read_only_fields = ["id", "is_automatic", "applied_at"]

    def validate(self, attrs):
        if attrs.get("penalty_type") == "percentage":
            validate_percentage(attrs.get("value"))
        else:
            validate_positive_amount(attrs.get("value"))
        return attrs


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id", "invoice", "amount", "method", "reference_number",
            "tracking_code", "paid_at", "created_by", "status",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "paid_at", "created_by", "status", "created_at", "updated_at"]

    def validate_amount(self, value):
        validate_positive_amount(value)
        return value


class ReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = ["id", "payment", "receipt_number", "issued_at", "pdf_file"]
        read_only_fields = fields


class InvoiceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            "id", "invoice_number", "residence", "township", "issue_date",
            "due_date", "status", "total", "paid_amount", "remaining_amount",
        ]
        read_only_fields = fields


class InvoiceDetailSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    discounts = DiscountSerializer(many=True, read_only=True)
    penalties = PenaltySerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "invoice_number", "residence", "township", "billing_cycle",
            "issue_date", "due_date", "status", "subtotal", "discount_total",
            "penalty_total", "total", "paid_amount", "remaining_amount",
            "notes", "created_by", "created_at", "updated_at",
            "items", "discounts", "penalties", "payments",
        ]
        read_only_fields = [
            "id", "invoice_number", "subtotal", "discount_total", "penalty_total",
            "total", "paid_amount", "remaining_amount", "status", "created_by",
            "created_at", "updated_at",
        ]


class InvoiceCreateSerializer(serializers.ModelSerializer):
    """
    Accepts nested items on creation; delegates actual persistence and
    total calculation to services.InvoiceService.create_invoice so the
    same rules apply whether an invoice is created via API, admin, or
    an automatic billing cycle.
    """

    items = InvoiceItemSerializer(many=True, required=False)

    class Meta:
        model = Invoice
        fields = [
            "id", "residence", "township", "due_date", "notes", "items",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        from billing.services import InvoiceService

        items_data = validated_data.pop("items", [])
        request = self.context.get("request")
        return InvoiceService.create_invoice(
            residence=validated_data["residence"],
            township=validated_data["township"],
            due_date=validated_data.get("due_date"),
            notes=validated_data.get("notes", ""),
            created_by=getattr(request, "user", None) if request else None,
            items=[
                {
                    "charge_type": item["charge_type"],
                    "title": item["title"],
                    "description": item.get("description", ""),
                    "quantity": item.get("quantity", 1),
                    "unit_price": item["unit_price"],
                }
                for item in items_data
            ],
        )


class RecordPaymentSerializer(serializers.Serializer):
    """Write-only input serializer for the payments/record action."""

    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    method = serializers.ChoiceField(choices=Payment._meta.get_field("method").choices)
    reference_number = serializers.CharField(required=False, allow_blank=True)
    tracking_code = serializers.CharField(required=False, allow_blank=True)
    mark_successful = serializers.BooleanField(default=False)

    def validate_amount(self, value):
        validate_positive_amount(value)
        return value
