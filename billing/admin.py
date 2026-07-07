from django.contrib import admin
from django.utils.html import format_html

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


@admin.register(ChargeType)
class ChargeTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    readonly_fields = ("id", "slug", "created_at", "updated_at")
    prepopulated_fields = {}


@admin.register(ChargeRule)
class ChargeRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "charge_type", "calculation_method", "base_amount", "is_active")
    list_filter = ("calculation_method", "is_active", "charge_type")
    search_fields = ("name", "charge_type__name")
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("charge_type",)


@admin.register(BillingCycle)
class BillingCycleAdmin(admin.ModelAdmin):
    list_display = (
        "name", "charge_rule", "frequency", "next_run_date",
        "auto_generate", "is_active",
    )
    list_filter = ("frequency", "auto_generate", "is_active")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("charge_rule",)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ("amount",)
    fields = ("charge_type", "title", "quantity", "unit_price", "amount")


class DiscountInline(admin.TabularInline):
    model = Discount
    extra = 0
    fields = ("discount_type", "value", "reason", "applied_by")


class PenaltyInline(admin.TabularInline):
    model = Penalty
    extra = 0
    fields = ("penalty_type", "value", "reason", "is_automatic")


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ("amount", "method", "status", "paid_at")
    readonly_fields = ("status", "paid_at")
    show_change_link = True


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number", "residence", "township", "status_badge",
        "issue_date", "due_date", "total", "paid_amount", "remaining_amount",
    )
    list_filter = ("status", "township", "issue_date", "due_date")
    search_fields = ("invoice_number", "residence__id", "notes")
    date_hierarchy = "issue_date"
    readonly_fields = (
        "id", "invoice_number", "subtotal", "discount_total", "penalty_total",
        "total", "paid_amount", "remaining_amount", "created_at", "updated_at",
    )
    inlines = [InvoiceItemInline, DiscountInline, PenaltyInline, PaymentInline]
    autocomplete_fields = ("residence", "township", "billing_cycle")

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "draft": "#9CA3AF", "issued": "#3B82F6", "partially_paid": "#F59E0B",
            "paid": "#10B981", "overdue": "#EF4444", "cancelled": "#6B7280",
        }
        color = colors.get(obj.status, "#000")
        return format_html(
            '<span style="color:{}; font-weight:600">{}</span>',
            color, obj.get_status_display(),
        )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "invoice", "amount", "method", "status", "paid_at", "created_by",
    )
    list_filter = ("status", "method")
    search_fields = ("invoice__invoice_number", "reference_number", "tracking_code")
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("invoice", "created_by")


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "payment", "issued_at")
    search_fields = ("receipt_number", "payment__invoice__invoice_number")
    readonly_fields = ("id", "receipt_number", "issued_at")


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("invoice", "discount_type", "value", "applied_by", "created_at")
    list_filter = ("discount_type",)
    search_fields = ("invoice__invoice_number",)
    autocomplete_fields = ("invoice", "applied_by")


@admin.register(Penalty)
class PenaltyAdmin(admin.ModelAdmin):
    list_display = ("invoice", "penalty_type", "value", "is_automatic", "applied_at")
    list_filter = ("penalty_type", "is_automatic")
    search_fields = ("invoice__invoice_number",)
    autocomplete_fields = ("invoice",)
