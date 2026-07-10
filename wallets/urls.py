from rest_framework.routers import DefaultRouter

from .views import (
    WalletViewSet,
    WalletTransactionViewSet,
    SettlementViewSet,
    CommissionRuleViewSet,
    CommissionTransactionViewSet,
    PaymentGatewayViewSet,
    GatewayTransactionViewSet,
    GatewayCallbackViewSet,
    WithdrawalRequestViewSet,
)

router = DefaultRouter()

router.register(
    "wallets",
    WalletViewSet,
)

router.register(
    "transactions",
    WalletTransactionViewSet,
)

router.register(
    "settlements",
    SettlementViewSet,
)

router.register(
    "commission-rules",
    CommissionRuleViewSet,
)

router.register(
    "commissions",
    CommissionTransactionViewSet,
)

router.register(
    "payment-gateways",
    PaymentGatewayViewSet,
)

router.register(
    "gateway-transactions",
    GatewayTransactionViewSet,
)

router.register(
    "gateway-callbacks",
    GatewayCallbackViewSet,
)

router.register(
    "withdraw-requests",
    WithdrawalRequestViewSet,
)



urlpatterns = router.urls

from django.urls import path
from .views import PaymentCallbackView

urlpatterns += [
    path(
        "payment/callback/",
        PaymentCallbackView.as_view(),
        name="wallet-payment-callback",
    ),
]

from .callback_views import wallet_payment_callback
urlpatterns += [
    path(
        "callback/",
        wallet_payment_callback,
        name="wallet-payment-callback",
    ),
]