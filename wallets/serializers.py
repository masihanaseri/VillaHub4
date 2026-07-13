from decimal import Decimal

from rest_framework import serializers

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


class WalletSerializer(serializers.ModelSerializer):

    class Meta:

        model = Wallet

        fields = "__all__"

        read_only_fields = (
            "id",
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
            "id",
            "internal_reference",
            "balance_before",
            "balance_after",
            "status",
            "authority",
            "gateway_ref_id",
            "gateway_name",
            "gateway_response",
            "paid_at",
            "verified_at",
            "failed_at",
            "failure_reason",
            "created_at",
            "updated_at",
        )


class DepositRequestSerializer(serializers.Serializer):
    """Validates input for the manual/instant deposit action."""

    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    description = serializers.CharField(required=False, allow_blank=True, default="")


class WithdrawRequestSerializer(serializers.Serializer):

    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    description = serializers.CharField(required=False, allow_blank=True, default="")


class TransferRequestSerializer(serializers.Serializer):

    destination_wallet = serializers.PrimaryKeyRelatedField(queryset=Wallet.objects.all())
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    description = serializers.CharField(required=False, allow_blank=True, default="")


class OnlineDepositRequestSerializer(serializers.Serializer):

    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    description = serializers.CharField(required=False, allow_blank=True, default="")


class SettlementSerializer(serializers.ModelSerializer):

    class Meta:

        model = Settlement

        fields = "__all__"

        read_only_fields = (
            "id",
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

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class PaymentGatewaySerializer(serializers.ModelSerializer):

    class Meta:

        model = PaymentGateway

        fields = "__all__"

        # Secrets are write-only for staff, never exposed back in a
        # GET response body.
        extra_kwargs = {
            "merchant_id": {"write_only": True},
            "sandbox_merchant_id": {"write_only": True},
            "production_merchant_id": {"write_only": True},
            "api_key": {"write_only": True},
        }


class GatewayTransactionSerializer(serializers.ModelSerializer):

    class Meta:

        model = GatewayTransaction

        fields = "__all__"

        read_only_fields = (
            "id",
            "authority",
            "ref_id",
            "is_success",
            "is_verified",
            "is_wallet_updated",
            "raw_request",
            "raw_response",
            "created_at",
            "updated_at",
        )


class GatewayCallbackSerializer(serializers.ModelSerializer):

    class Meta:

        model = GatewayCallback

        fields = "__all__"

        # NOTE: this must be an explicit tuple, not a reference to the
        # `fields` name above. `read_only_fields = fields` previously
        # bound to the *string* "__all__" (DRF requires a list/tuple
        # here), which raised `TypeError` the first time any view
        # instantiated this serializer (e.g. GatewayCallbackViewSet.list()).
        read_only_fields = (
            "id",
            "gateway_transaction",
            "raw_data",
            "ip_address",
            "user_agent",
            "processed",
            "created_at",
            "updated_at",
        )


class WithdrawalRequestSerializer(serializers.ModelSerializer):

    class Meta:

        model = WithdrawalRequest

        fields = "__all__"

        read_only_fields = (
            "id",
            "wallet",
            # `amount` is fixed at creation time (WithdrawalRequestCreateSerializer
            # -> WithdrawalService.create_request, which validates it against
            # the wallet's balance and the configured minimum). Leaving it
            # writable here would let the owner of a still-PENDING request
            # silently bump the amount after the fact, bypassing that
            # validation right up until staff approves/pays it.
            "amount",
            "status",
            "wallet_transaction",
            "approved_by",
            "approved_at",
            "paid_by",
            "paid_at",
            "tracking_code",
            "bank_reference",
            "reject_reason",
            "created_at",
            "updated_at",
        )


class WithdrawalRequestCreateSerializer(serializers.Serializer):

    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    bank_name = serializers.CharField(required=False, allow_blank=True, default="")
    account_owner = serializers.CharField(required=False, allow_blank=True, default="")
    card_number = serializers.CharField(required=False, allow_blank=True, default="")
    sheba_number = serializers.CharField(required=False, allow_blank=True, default="")
    description = serializers.CharField(required=False, allow_blank=True, default="")


class WithdrawalRequestPaySerializer(serializers.Serializer):

    tracking_code = serializers.CharField(required=False, allow_blank=True, default="")


class WithdrawalRequestRejectSerializer(serializers.Serializer):

    reason = serializers.CharField(required=False, allow_blank=True, default="")
