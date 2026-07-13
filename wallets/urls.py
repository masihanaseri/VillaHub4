from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CommissionRuleViewSet,
    CommissionTransactionViewSet,
    GatewayCallbackViewSet,
    GatewayTransactionViewSet,
    PaymentCallbackView,
    PaymentGatewayViewSet,
    SettlementViewSet,
    WalletTransactionViewSet,
    WalletViewSet,
    WithdrawalRequestViewSet,
)

router = DefaultRouter()

router.register(
    "wallets",
    WalletViewSet,
    basename="wallet",
)

router.register(
    "transactions",
    WalletTransactionViewSet,
    basename="wallet-transaction",
)

router.register(
    "settlements",
    SettlementViewSet,
    basename="settlement",
)

router.register(
    "commission-rules",
    CommissionRuleViewSet,
    basename="commission-rule",
)

router.register(
    "commissions",
    CommissionTransactionViewSet,
    basename="commission-transaction",
)

router.register(
    "payment-gateways",
    PaymentGatewayViewSet,
    basename="payment-gateway",
)

router.register(
    "gateway-transactions",
    GatewayTransactionViewSet,
    basename="gateway-transaction",
)

router.register(
    "gateway-callbacks",
    GatewayCallbackViewSet,
    basename="gateway-callback",
)

router.register(
    "withdraw-requests",
    WithdrawalRequestViewSet,
    basename="withdrawal-request",
)

urlpatterns = router.urls

urlpatterns += [
    # Single, idempotent HTTP entry point the payment gateway redirects
    # to after a payment attempt. Verification + wallet crediting is
    # handled entirely by PaymentGatewayService; see PaymentCallbackView.
    #
    # NOTE: an older second registration of this same URL name used to
    # live here, pointing at `wallets.callback_views.wallet_payment_callback`
    # — a function that was never defined in that module (it only ever
    # exposed `payment_success_page` / `payment_failed_page`), so
    # importing this file raised ImportError and the app couldn't start.
    # It also silently shadowed this route via a duplicate URL name.
    # Removed as dead/broken leftover code; PaymentCallbackView below is
    # the one and only "wallet-payment-callback" implementation.
    path(
        "payment/callback/",
        PaymentCallbackView.as_view(),
        name="wallet-payment-callback",
    ),
]
