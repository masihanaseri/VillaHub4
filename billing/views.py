"""
DRF views. No business logic here - every non-trivial action delegates
to billing.services. Views only: authenticate/authorize, parse input,
call a service, shape output.
"""
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters as drf_filters, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from billing.filters import (
    InvoiceFilter,
    PaymentFilter,
    ChargeRuleFilter,
    BillingCycleFilter,
)
from billing.models import (
    ChargeType,
    ChargeRule,
    BillingCycle,
    Invoice,
    Discount,
    Penalty,
    Payment,
    Receipt,
)
from billing.permissions import IsBillingStaff, IsBillingStaffOrReadOnlyOwner, _is_finance_staff
from billing.serializers import (
    ChargeTypeSerializer,
    ChargeRuleSerializer,
    BillingCycleSerializer,
    InvoiceListSerializer,
    InvoiceDetailSerializer,
    InvoiceCreateSerializer,
    InvoiceItemSerializer,
    DiscountSerializer,
    PenaltySerializer,
    PaymentSerializer,
    ReceiptSerializer,
    RecordPaymentSerializer,
)
from billing.services import InvoiceService, PaymentService, ReportService


class BillingPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class ChargeTypeViewSet(viewsets.ModelViewSet):
    queryset = ChargeType.objects.all()
    serializer_class = ChargeTypeSerializer
    permission_classes = [IsBillingStaff]
    pagination_class = BillingPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]


class ChargeRuleViewSet(viewsets.ModelViewSet):
    queryset = ChargeRule.objects.select_related("charge_type").all()
    serializer_class = ChargeRuleSerializer
    permission_classes = [IsBillingStaff]
    pagination_class = BillingPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = ChargeRuleFilter
    search_fields = ["name", "charge_type__name"]
    ordering_fields = ["name", "created_at"]


class BillingCycleViewSet(viewsets.ModelViewSet):
    queryset = BillingCycle.objects.select_related("charge_rule").all()
    serializer_class = BillingCycleSerializer
    permission_classes = [IsBillingStaff]
    pagination_class = BillingPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = BillingCycleFilter
    search_fields = ["name"]
    ordering_fields = ["next_run_date", "start_date"]


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related("residence", "township", "billing_cycle").all()
    permission_classes = [IsBillingStaffOrReadOnlyOwner]
    pagination_class = BillingPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = InvoiceFilter
    search_fields = ["invoice_number", "notes"]
    ordering_fields = ["issue_date", "due_date", "total", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_finance_staff(user):
            return qs
        # Resident self-service scoping to their own residence(s).
        return qs.filter(residence__user_id=user.id)

    def get_serializer_class(self):
        if self.action == "list":
            return InvoiceListSerializer
        if self.action == "create":
            return InvoiceCreateSerializer
        return InvoiceDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = serializer.save()
        return Response(
            InvoiceDetailSerializer(invoice).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        invoice = self.get_object()
        invoice = InvoiceService.issue(invoice)
        return Response(InvoiceDetailSerializer(invoice).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        invoice = self.get_object()
        invoice = InvoiceService.cancel(invoice)
        return Response(InvoiceDetailSerializer(invoice).data)

    @action(detail=True, methods=["post"], url_path="items")
    def add_item(self, request, pk=None):
        invoice = self.get_object()
        serializer = InvoiceItemSerializer(data={**request.data, "invoice": invoice.id})
        serializer.is_valid(raise_exception=True)
        item = InvoiceService.add_item(
            invoice,
            charge_type=serializer.validated_data["charge_type"],
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            quantity=serializer.validated_data.get("quantity", 1),
            unit_price=serializer.validated_data["unit_price"],
        )
        return Response(InvoiceItemSerializer(item).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def discounts(self, request, pk=None):
        invoice = self.get_object()
        serializer = DiscountSerializer(data={**request.data, "invoice": invoice.id})
        serializer.is_valid(raise_exception=True)
        discount = InvoiceService.apply_discount(
            invoice,
            discount_type=serializer.validated_data["discount_type"],
            value=serializer.validated_data["value"],
            reason=serializer.validated_data.get("reason", ""),
            applied_by=request.user,
        )
        return Response(DiscountSerializer(discount).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def penalties(self, request, pk=None):
        invoice = self.get_object()
        serializer = PenaltySerializer(data={**request.data, "invoice": invoice.id})
        serializer.is_valid(raise_exception=True)
        penalty = InvoiceService.apply_penalty(
            invoice,
            penalty_type=serializer.validated_data["penalty_type"],
            value=serializer.validated_data["value"],
            reason=serializer.validated_data.get("reason", ""),
        )
        return Response(PenaltySerializer(penalty).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="payments")
    def record_payment(self, request, pk=None):
        invoice = self.get_object()
        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        payment = PaymentService.record_payment(
            invoice=invoice,
            amount=data["amount"],
            method=data["method"],
            reference_number=data.get("reference_number", ""),
            tracking_code=data.get("tracking_code", ""),
            created_by=request.user,
            status="success" if data.get("mark_successful") else "pending",
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Payments are created via Invoice.record_payment; this exposes
    read + status-transition actions."""

    queryset = Payment.objects.select_related("invoice").all()
    serializer_class = PaymentSerializer
    permission_classes = [IsBillingStaff]
    pagination_class = BillingPagination
    filter_backends = [DjangoFilterBackend, drf_filters.OrderingFilter]
    filterset_class = PaymentFilter
    ordering_fields = ["created_at", "paid_at", "amount"]

    @action(detail=True, methods=["post"])
    def mark_success(self, request, pk=None):
        payment = PaymentService.mark_success(self.get_object())
        return Response(PaymentSerializer(payment).data)

    @action(detail=True, methods=["post"])
    def mark_failed(self, request, pk=None):
        payment = PaymentService.mark_failed(self.get_object(), reason=request.data.get("reason", ""))
        return Response(PaymentSerializer(payment).data)

    @action(detail=True, methods=["post"])
    def refund(self, request, pk=None):
        payment = PaymentService.refund(self.get_object())
        return Response(PaymentSerializer(payment).data)


class ReceiptViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Receipt.objects.select_related("payment").all()
    serializer_class = ReceiptSerializer
    permission_classes = [IsBillingStaffOrReadOnlyOwner]
    pagination_class = BillingPagination

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_finance_staff(user):
            return qs
        return qs.filter(payment__invoice__residence__user_id=user.id)


class FinanceReportView(viewsets.ViewSet):
    """
    Read-only reporting endpoints per spec section 10/12 ("prepare
    architecture, no dashboard/AI implementation yet"). Each action is a
    thin pass-through to ReportService.
    """

    permission_classes = [IsBillingStaff]

    @action(detail=False, methods=["get"])
    def income(self, request):
        start = request.query_params.get("start_date")
        end = request.query_params.get("end_date")
        return Response({"income": ReportService.total_income(start, end)})

    @action(detail=False, methods=["get"])
    def outstanding_debts(self, request):
        township_id = request.query_params.get("township")
        return Response({"outstanding_debts": ReportService.outstanding_debts(township_id)})

    @action(detail=False, methods=["get"])
    def collection_rate(self, request):
        start = request.query_params.get("start_date")
        end = request.query_params.get("end_date")
        return Response({"collection_rate_percent": ReportService.collection_rate(start, end)})

    @action(detail=False, methods=["get"])
    def top_debtors(self, request):
        limit = int(request.query_params.get("limit", 10))
        return Response(list(ReportService.top_debtors(limit)))
