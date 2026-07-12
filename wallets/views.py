import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import GatewayTransactionFilter, WalletTransactionFilter, WithdrawalRequestFilter
from .models import (
    CommissionRule,
    CommissionTransaction,
    GatewayCallback,
    GatewayTransaction,
    PaymentGateway,
    Settlement,
    Wallet,
    WalletTransaction,
    WalletType,
    WithdrawalRequest,
)
from .permissions import (
    IsFinanceStaff,
    IsWalletOwner,
    IsWalletTransactionOwner,
    ReadOnlyOrFinanceStaff,
)
from .serializers import (
    CommissionRuleSerializer,
    CommissionTransactionSerializer,
    DepositRequestSerializer,
    GatewayCallbackSerializer,
    GatewayTransactionSerializer,
    OnlineDepositRequestSerializer,
    PaymentGatewaySerializer,
    SettlementSerializer,
    TransferRequestSerializer,
    WalletSerializer,
    WalletTransactionSerializer,
    WithdrawalRequestCreateSerializer,
    WithdrawalRequestPaySerializer,
    WithdrawalRequestRejectSerializer,
    WithdrawalRequestSerializer,
    WithdrawRequestSerializer,
)
from .services import (
    InsufficientBalanceError,
    PaymentGatewayService,
    PaymentVerificationError,
    SettlementService,
    TransferService,
    WalletService,
)
from .services.settlement_service import SettlementError
from .services.withdrawal_service import WithdrawalError, WithdrawalService

logger = logging.getLogger("wallets.views")


def _error(message, http_status=status.HTTP_400_BAD_REQUEST):

    return Response({"error": message}, status=http_status)


# ----------------------------------------
# Wallet
# ----------------------------------------

class WalletViewSet(viewsets.ModelViewSet):

    serializer_class = WalletSerializer

    permission_classes = [IsAuthenticated, IsWalletOwner]

    def get_queryset(self):

        user = self.request.user

        if user.is_superuser or user.is_staff:
            return Wallet.objects.all()

        return Wallet.objects.filter(user=user)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsFinanceStaff])
    def deposit(self, request, pk=None):
        """Manual ledger credit. Finance staff only."""

        wallet = self.get_object()
        serializer = DepositRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        WalletService.deposit(
            wallet,
            serializer.validated_data["amount"],
            serializer.validated_data["description"],
        )
        wallet.refresh_from_db()

        return Response(WalletSerializer(wallet).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsFinanceStaff])
    def withdraw(self, request, pk=None):
        """Manual ledger debit. Finance staff only."""

        wallet = self.get_object()
        serializer = WithdrawRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            WalletService.withdraw(
                wallet,
                serializer.validated_data["amount"],
                serializer.validated_data["description"],
            )
        except InsufficientBalanceError as exc:
            return _error(str(exc))

        wallet.refresh_from_db()

        return Response(WalletSerializer(wallet).data)

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        """Owner-initiated transfer out of their own wallet."""

        wallet = self.get_object()
        serializer = TransferRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        destination = serializer.validated_data["destination_wallet"]

        try:
            TransferService.transfer(
                wallet,
                destination,
                serializer.validated_data["amount"],
                serializer.validated_data["description"],
            )
        except InsufficientBalanceError as exc:
            return _error(str(exc))
        except ValueError as exc:
            return _error(str(exc))

        wallet.refresh_from_db()

        return Response({"success": True, "balance": wallet.balance})

    @action(detail=True, methods=["post"])
    def online_deposit(self, request, pk=None):
        """Owner-initiated top-up through the active payment gateway."""

        wallet = self.get_object()
        serializer = OnlineDepositRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wallet_transaction = WalletService.create_pending_transaction(
            wallet=wallet,
            amount=serializer.validated_data["amount"],
            description=serializer.validated_data["description"],
        )

        try:
            payment_url = PaymentGatewayService.create_payment(
                wallet_transaction,
                request,
            )
        except PaymentVerificationError as exc:
            return _error(str(exc), status.HTTP_502_BAD_GATEWAY)

        return Response(
            {
                "payment_url": payment_url,
                "transaction_id": wallet_transaction.id,
                "internal_reference": wallet_transaction.internal_reference,
            }
        )


# ----------------------------------------
# Wallet Transaction (read-only ledger)
# ----------------------------------------

class WalletTransactionViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = WalletTransactionSerializer

    permission_classes = [IsAuthenticated, IsWalletTransactionOwner]

    filter_backends = [
        DjangoFilterBackend,
        drf_filters.OrderingFilter,
        drf_filters.SearchFilter,
    ]

    filterset_class = WalletTransactionFilter

    ordering_fields = ["created_at", "amount", "status"]

    ordering = ["-created_at"]

    search_fields = ["internal_reference", "authority", "gateway_ref_id", "reference", "description"]

    def get_queryset(self):

        user = self.request.user

        qs = WalletTransaction.objects.select_related("wallet", "gateway", "invoice")

        if user.is_superuser or user.is_staff:
            return qs

        return qs.filter(wallet__user=user)


# ----------------------------------------
# Settlement
# ----------------------------------------

class SettlementViewSet(viewsets.ModelViewSet):

    serializer_class = SettlementSerializer

    permission_classes = [IsAuthenticated, ReadOnlyOrFinanceStaff]

    def get_queryset(self):

        user = self.request.user

        if user.is_superuser or user.is_staff:
            return Settlement.objects.select_related("wallet")

        return Settlement.objects.select_related("wallet").filter(wallet__user=user)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsFinanceStaff])
    def approve(self, request, pk=None):

        settlement = self.get_object()

        try:
            SettlementService.approve(settlement)
        except SettlementError as exc:
            return _error(str(exc))

        return Response(SettlementSerializer(settlement).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsFinanceStaff])
    def pay(self, request, pk=None):

        settlement = self.get_object()
        tracking_code = request.data.get("tracking_code", "")

        try:
            SettlementService.pay(settlement, tracking_code)
        except (SettlementError, InsufficientBalanceError) as exc:
            return _error(str(exc))

        return Response(SettlementSerializer(settlement).data)


# ----------------------------------------
# Commission
# ----------------------------------------

class CommissionRuleViewSet(viewsets.ModelViewSet):

    queryset = CommissionRule.objects.select_related("township")

    serializer_class = CommissionRuleSerializer

    permission_classes = [IsAuthenticated, ReadOnlyOrFinanceStaff]


class CommissionTransactionViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = CommissionTransactionSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        user = self.request.user

        qs = CommissionTransaction.objects.select_related("township", "wallet_transaction")

        if user.is_superuser or user.is_staff:
            return qs

        # A township "owner" is a user with a TOWNSHIP wallet for that
        # township; scope visibility to their own township's commissions.
        owned_township_ids = Wallet.objects.filter(
            user=user,
            wallet_type=WalletType.TOWNSHIP,
        ).values_list("township_id", flat=True)

        return qs.filter(township_id__in=owned_township_ids)


# ----------------------------------------
# Payment Gateway (admin-managed)
# ----------------------------------------

class PaymentGatewayViewSet(viewsets.ModelViewSet):

    queryset = PaymentGateway.objects.all()

    serializer_class = PaymentGatewaySerializer

    permission_classes = [IsAuthenticated, ReadOnlyOrFinanceStaff]


class GatewayTransactionViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = GatewayTransactionSerializer

    permission_classes = [IsAuthenticated, IsWalletTransactionOwner]

    filter_backends = [DjangoFilterBackend]

    filterset_class = GatewayTransactionFilter

    def get_queryset(self):

        user = self.request.user

        qs = GatewayTransaction.objects.select_related("wallet", "gateway", "wallet_transaction")

        if user.is_superuser or user.is_staff:
            return qs

        return qs.filter(wallet__user=user)


class GatewayCallbackViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = GatewayCallback.objects.select_related("gateway_transaction")

    serializer_class = GatewayCallbackSerializer

    permission_classes = [IsAuthenticated, IsFinanceStaff]


# ----------------------------------------
# Withdrawal Request
# ----------------------------------------

class WithdrawalRequestViewSet(viewsets.ModelViewSet):

    serializer_class = WithdrawalRequestSerializer

    permission_classes = [IsAuthenticated, IsWalletTransactionOwner]

    filter_backends = [DjangoFilterBackend, drf_filters.OrderingFilter]

    filterset_class = WithdrawalRequestFilter

    ordering_fields = ["created_at", "amount", "status"]

    ordering = ["-created_at"]

    def get_queryset(self):

        user = self.request.user

        qs = WithdrawalRequest.objects.select_related("wallet", "wallet_transaction")

        if user.is_superuser or user.is_staff:
            return qs

        return qs.filter(wallet__user=user)

    @action(detail=False, methods=["post"])
    def create_request(self, request):

        serializer = WithdrawalRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            withdrawal_request = WithdrawalService.create_request(
                user=request.user,
                **serializer.validated_data,
            )
        except Wallet.DoesNotExist:
            return _error("No active resident wallet found.", status.HTTP_404_NOT_FOUND)
        except InsufficientBalanceError as exc:
            return _error(str(exc))

        return Response(
            WithdrawalRequestSerializer(withdrawal_request).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsFinanceStaff])
    def approve(self, request, pk=None):

        withdrawal_request = self.get_object()

        try:
            WithdrawalService.approve(withdrawal_request, approved_by=request.user)
        except WithdrawalError as exc:
            return _error(str(exc))

        return Response(WithdrawalRequestSerializer(withdrawal_request).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsFinanceStaff])
    def pay(self, request, pk=None):

        withdrawal_request = self.get_object()
        serializer = WithdrawalRequestPaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            withdrawal_request, wallet_transaction = WithdrawalService.pay(
                withdrawal_request,
                paid_by=request.user,
                tracking_code=serializer.validated_data["tracking_code"],
            )
        except (WithdrawalError, InsufficientBalanceError) as exc:
            return _error(str(exc))

        return Response(
            {
                "success": True,
                "balance": withdrawal_request.wallet.balance,
                "transaction_id": wallet_transaction.id,
                "internal_reference": wallet_transaction.internal_reference,
            }
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsFinanceStaff])
    def reject(self, request, pk=None):

        withdrawal_request = self.get_object()
        serializer = WithdrawalRequestRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            WithdrawalService.reject(
                withdrawal_request,
                reason=serializer.validated_data["reason"],
            )
        except WithdrawalError as exc:
            return _error(str(exc))

        return Response(WithdrawalRequestSerializer(withdrawal_request).data)


# ----------------------------------------
# Payment Callback (gateway redirect / server callback)
# ----------------------------------------

class PaymentCallbackView(APIView):
    """
    Single, idempotent entry point for gateway callbacks. Replaces the
    two previously-duplicated implementations
    (``callback_views.wallet_payment_callback`` and the old
    class-based ``PaymentCallbackView``), both of which independently
    called ``verify_payment`` and could double-process the same
    callback or credit a wallet twice.
    """

    permission_classes = []
    authentication_classes = []

    def get(self, request):

        authority = request.GET.get("Authority")
        status_param = request.GET.get("Status")

        if not authority:
            return _error("Authority not found.", status.HTTP_400_BAD_REQUEST)

        try:
            gateway_transaction, wallet_transaction = PaymentGatewayService.handle_callback(
                authority=authority,
                gateway_status_param=status_param,
                request=request,
            )
        except GatewayTransaction.DoesNotExist:
            return _error("Transaction not found.", status.HTTP_404_NOT_FOUND)
        except PaymentVerificationError as exc:
            logger.warning("payment.callback.verification_error", extra={"error": str(exc)})
            return _error("Payment verification failed.", status.HTTP_502_BAD_GATEWAY)

        if not gateway_transaction.is_success:
            return Response({"success": False, "message": "Payment was not successful."})

        return Response(
            {
                "success": True,
                "reference": gateway_transaction.ref_id,
                "internal_reference": (
                    wallet_transaction.internal_reference if wallet_transaction else None
                ),
            }
        )
