import django_filters

from .models import GatewayTransaction, WalletTransaction, WithdrawalRequest


class WalletTransactionFilter(django_filters.FilterSet):

    created_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    min_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    max_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")

    class Meta:

        model = WalletTransaction

        fields = [
            "wallet",
            "transaction_type",
            "status",
            "gateway",
        ]


class WithdrawalRequestFilter(django_filters.FilterSet):

    created_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:

        model = WithdrawalRequest

        fields = [
            "status",
            "wallet",
        ]


class GatewayTransactionFilter(django_filters.FilterSet):

    class Meta:

        model = GatewayTransaction

        fields = [
            "gateway",
            "is_verified",
            "is_success",
        ]
