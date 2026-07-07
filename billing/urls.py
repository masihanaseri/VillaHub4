from django.urls import include, path
from rest_framework.routers import DefaultRouter

from billing import views

app_name = "billing"

router = DefaultRouter()
router.register("charge-types", views.ChargeTypeViewSet, basename="charge-type")
router.register("charge-rules", views.ChargeRuleViewSet, basename="charge-rule")
router.register("billing-cycles", views.BillingCycleViewSet, basename="billing-cycle")
router.register("invoices", views.InvoiceViewSet, basename="invoice")
router.register("payments", views.PaymentViewSet, basename="payment")
router.register("receipts", views.ReceiptViewSet, basename="receipt")
router.register("reports", views.FinanceReportView, basename="report")

urlpatterns = [
    path("", include(router.urls)),
]
