from django.contrib import admin

from .models import (
    Wallet,
    WalletTransaction,
    Settlement,
    CommissionRule,
    CommissionTransaction,
    PaymentGateway,
    GatewayTransaction,
    GatewayCallback,
    WithdrawalRequest,
)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "wallet_type",
        "user",
        "township",
        "balance",
        "is_active",
    )

    list_filter = (
        "wallet_type",
        "is_active",
    )

    search_fields = (
        "user__username",
        "township__name",
    )

    readonly_fields = (
        "uuid",
        "balance",
        "created_at",
        "updated_at",
    )


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "wallet",
        "transaction_type",
        "amount",
        "status",
        "gateway_name",
        "created_at",
    )

    list_filter = (
        "transaction_type",
        "status",
        "gateway_name",
    )

    search_fields = (
        "authority",
        "gateway_ref_id",
        "reference",
    )

    readonly_fields = (
        "balance_before",
        "balance_after",
        "authority",
        "gateway_ref_id",
        "paid_at",
        "verified_at",
        "created_at",
        "updated_at",
    )


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "wallet",
        "amount",
        "status",
        "paid_at",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "tracking_code",
    )


@admin.register(CommissionRule)
class CommissionRuleAdmin(admin.ModelAdmin):

    list_display = (
        "township",
        "monthly_subscription",
        "transaction_percent",
        "is_active",
    )


@admin.register(CommissionTransaction)
class CommissionTransactionAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "township",
        "amount",
        "percent",
        "created_at",
    )


@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "slug",
        "sandbox",
        "priority",
        "is_active",
    )

    list_filter = (
        "sandbox",
        "is_active",
    )

    search_fields = (
        "name",
        "slug",
    )


@admin.register(GatewayTransaction)
class GatewayTransactionAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "gateway",
        "authority",
        "amount",
        "is_verified",
        "created_at",
    )

    list_filter = (

        "is_verified",
        "gateway",
    )

    search_fields = (
        "authority",
        "ref_id",
    )

    readonly_fields = (
        "raw_request",
        "raw_response",
    )


@admin.register(GatewayCallback)
class GatewayCallbackAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "ip_address",
        "created_at",
    )

    readonly_fields = (
        "raw_data",
    )


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "wallet",
        "amount",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "wallet__user__username",
        "tracking_code",
        "bank_reference",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )