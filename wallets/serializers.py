from rest_framework import serializers

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


class WalletSerializer(serializers.ModelSerializer):

    class Meta:

        model = Wallet

        fields = "__all__"

        read_only_fields = (
            "uuid",
            "balance",
            "created_at",
            "updated_at",
        )


class WalletTransactionSerializer(serializers.ModelSerializer):

    class Meta:

        model = WalletTransaction

        fields = "__all__"

        read_only_fields = (
            "balance_before",
            "balance_after",
            "authority",
            "gateway_ref_id",
            "gateway_name",
            "paid_at",
            "verified_at",
            "status",
            "created_at",
            "updated_at",
        )


class SettlementSerializer(serializers.ModelSerializer):

    class Meta:

        model = Settlement

        fields = "__all__"

        read_only_fields = (
            "status",
            "tracking_code",
            "paid_at",
            "created_at",
            "updated_at",
        )


class CommissionRuleSerializer(serializers.ModelSerializer):

    class Meta:

        model = CommissionRule

        fields = "__all__"


class CommissionTransactionSerializer(serializers.ModelSerializer):

    class Meta:

        model = CommissionTransaction

        fields = "__all__"


class PaymentGatewaySerializer(serializers.ModelSerializer):

    class Meta:

        model = PaymentGateway

        fields = "__all__"

        read_only_fields = (
            "merchant_id",
            "sandbox_merchant_id",
            "production_merchant_id",
            "api_key",
        )        


class GatewayTransactionSerializer(serializers.ModelSerializer):

    class Meta:

        model = GatewayTransaction

        fields = "__all__"

        read_only_fields = (
            "authority",
            "ref_id",
            "success",
            "is_verified",
            "raw_request",
            "raw_response",
        )


class GatewayCallbackSerializer(serializers.ModelSerializer):

    class Meta:

        model = GatewayCallback

        fields = "__all__"


class WithdrawalRequestSerializer(serializers.ModelSerializer):

    class Meta:

        model = WithdrawalRequest

        fields = "__all__"

        read_only_fields = (
            "approved",
            "paid",
            "tracking_code",
        )