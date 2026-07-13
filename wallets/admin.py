from django.contrib import admin

from .models import (
    CommissionRule,
    CommissionTransaction,
    GatewayCallback,
    GatewayTransaction,
    PaymentGateway,
    Settlement,
    Wallet,
    WalletTransaction,
    WithdrawalRequest,
)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):

    list_display = ("id", "wallet_type", "user", "township", "balance", "is_active")

    list_filter = ("wallet_type", "is_active")

    search_fields = ("user__username", "township__name", "uuid")

    readonly_fields = ("uuid", "balance", "created_at", "updated_at")

    # Avoids one extra query per row for `user`/`township` in the
    # changelist (N+1) — both are rendered via list_display above.
    list_select_related = ("user", "township")


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):

    list_display = (
        "internal_reference",
        "wallet",
        "transaction_type",
        "amount",
        "status",
        "gateway_name",
        "created_at",
    )

    list_filter = ("transaction_type", "status", "gateway_name")

    search_fields = (
        "internal_reference",
        "authority",
        "gateway_ref_id",
        "reference",
    )

    readonly_fields = (
        "internal_reference",
        "balance_before",
        "balance_after",
        "authority",
        "gateway_ref_id",
        "gateway_response",
        "paid_at",
        "verified_at",
        "failed_at",
        "created_at",
        "updated_at",
    )

    date_hierarchy = "created_at"

    list_select_related = ("wallet",)


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):

    list_display = ("id", "wallet", "amount", "status", "paid_at")

    list_filter = ("status",)

    search_fields = ("tracking_code",)

    list_select_related = ("wallet",)


@admin.register(CommissionRule)
class CommissionRuleAdmin(admin.ModelAdmin):

    list_display = ("township", "monthly_subscription", "transaction_percent", "is_active")


@admin.register(CommissionTransaction)
class CommissionTransactionAdmin(admin.ModelAdmin):

    list_display = ("id", "township", "amount", "percent", "created_at")

    list_select_related = ("township",)


@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):

    list_display = ("name", "slug", "sandbox", "priority", "is_active")

    list_filter = ("sandbox", "is_active")

    search_fields = ("name", "slug")


@admin.register(GatewayTransaction)
class GatewayTransactionAdmin(admin.ModelAdmin):

    list_display = ("id", "gateway", "authority", "amount", "is_success", "is_verified", "created_at")

    list_filter = ("is_verified", "is_success", "gateway")

    search_fields = ("authority", "ref_id")

    readonly_fields = ("raw_request", "raw_response")

    list_select_related = ("gateway",)


@admin.register(GatewayCallback)
class GatewayCallbackAdmin(admin.ModelAdmin):

    list_display = ("id", "gateway_transaction", "ip_address", "processed", "created_at")

    readonly_fields = ("raw_data",)

    list_select_related = ("gateway_transaction",)


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):

    list_display = ("id", "wallet", "amount", "status", "created_at")

    list_filter = ("status", "created_at")

    search_fields = ("wallet__user__username", "tracking_code", "bank_reference")

    readonly_fields = ("created_at", "updated_at")

    list_select_related = ("wallet",)
