from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets
from .payment_service import PaymentGatewayService
from rest_framework.views import APIView
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import WalletType
from django.utils import timezone
from .models import TransactionType


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

from .serializers import (
    WalletSerializer,
    WalletTransactionSerializer,
    SettlementSerializer,
    CommissionRuleSerializer,
    CommissionTransactionSerializer,
    PaymentGatewaySerializer,
    GatewayTransactionSerializer,
    GatewayCallbackSerializer,
    WithdrawalRequestSerializer,
)

from .services import (
    WalletService,
    SettlementService,
)


class WalletViewSet(viewsets.ModelViewSet):

    queryset = Wallet.objects.all()

    serializer_class = WalletSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    @action(detail=True, methods=["post"])

    def deposit(self, request, pk=None):

        wallet = self.get_object()

        WalletService.deposit(

            wallet,

            request.data["amount"],

            request.data.get("description", ""),

        )

        return Response(

            WalletSerializer(wallet).data

        )

    @action(detail=True, methods=["post"])

    def withdraw(self, request, pk=None):

        wallet = self.get_object()

        WalletService.withdraw(

            wallet,

            request.data["amount"],

            request.data.get("description", ""),

        )

        return Response(

            WalletSerializer(wallet).data

        )

    @action(detail=True, methods=["post"])

    def transfer(self, request, pk=None):

        wallet = self.get_object()

        destination = Wallet.objects.get(

            id=request.data["destination_wallet"]

        )


        WalletService.transfer(

            wallet,

            destination,

            request.data["amount"],

        )

        return Response(

            {"success": True}

        )

    @action(
        detail=True,
        methods=["post"],
    )
    def online_deposit(self, request, pk=None):

        wallet = self.get_object()

        transaction = WalletService.create_deposit_transaction(
            wallet=wallet,
            amount=request.data["amount"],
            description=request.data.get(
                "description",
                "",
            ),
        )

        payment_url = PaymentGatewayService.create_payment(
            transaction,
            request,
        )

        return Response(
            {
                "payment_url": payment_url,
                "transaction_id": transaction.id,
            }
        )




class WalletTransactionViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = WalletTransaction.objects.all()

    serializer_class = WalletTransactionSerializer

    permission_classes = [
        IsAuthenticated,
    ]


class SettlementViewSet(viewsets.ModelViewSet):

    queryset = Settlement.objects.all()

    serializer_class = SettlementSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    @action(detail=True, methods=["post"])

    def approve(self, request, pk=None):

        settlement = self.get_object()

        SettlementService.approve(

            settlement,

        )

        return Response(

            SettlementSerializer(settlement).data

        )

    @action(detail=True, methods=["post"])

    def pay(self, request, pk=None):

        settlement = self.get_object()

        SettlementService.pay(

            settlement,

            request.data["tracking_code"],

        )

        return Response(

            SettlementSerializer(settlement).data

        )
class CommissionRuleViewSet(viewsets.ModelViewSet):

    queryset = CommissionRule.objects.all()

    serializer_class = CommissionRuleSerializer

    permission_classes = [
        IsAuthenticated,
    ]


class CommissionTransactionViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = CommissionTransaction.objects.all()

    serializer_class = CommissionTransactionSerializer

    permission_classes = [
        IsAuthenticated,
    ]

class PaymentGatewayViewSet(viewsets.ModelViewSet):

    queryset = PaymentGateway.objects.all()

    serializer_class = PaymentGatewaySerializer

    permission_classes = [
        IsAuthenticated,
    ]


class GatewayTransactionViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = GatewayTransaction.objects.all()

    serializer_class = GatewayTransactionSerializer

    permission_classes = [
        IsAuthenticated,
    ]


class GatewayCallbackViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = GatewayCallback.objects.all()

    serializer_class = GatewayCallbackSerializer

    permission_classes = [
        IsAuthenticated,
    ]

class WithdrawalRequestViewSet(viewsets.ModelViewSet):

    queryset = WithdrawalRequest.objects.all()

    serializer_class = WithdrawalRequestSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    filterset_fields = [
        "status",
    ]

    @action(detail=False, methods=["post"])
    def create_request(self, request):

        wallet = get_object_or_404(
            Wallet,
            user=request.user,
            wallet_type=WalletType.RESIDENT,
            is_active=True,
        )

        amount = request.data.get("amount")

        if amount is None:
            return Response(
                {
                    "error": "amount is required"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount = float(amount)

        if amount <= 0:
            return Response(
                {
                    "error": "amount must be greater than zero"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if amount > wallet.balance:
            return Response(
                {
                    "error": "Insufficient balance"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        withdraw_request = WithdrawalRequest.objects.create(
            wallet=wallet,
            amount=amount,
            status=WithdrawalRequest.Status.PENDING,

            bank_name=request.data.get(
                "bank_name",
                "",
            ),

            account_owner=request.data.get(
                "account_owner",
                "",
            ),

            card_number=request.data.get(
                "card_number",
                "",
            ),

            sheba_number=request.data.get(
                "sheba_number",
                "",
            ),

            description=request.data.get(
                "description",
                "",
            ),
        )

        return Response(
            {
                "request_id": withdraw_request.id,
                "status": withdraw_request.status,
                "amount": withdraw_request.amount,
            }
        )
    
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):




        if not request.user.is_staff:

            return Response(
                {
                    "error": "Only admin can approve withdrawal requests."
                },
                status=status.HTTP_403_FORBIDDEN,
            )


        withdraw_request = self.get_object()

        if withdraw_request.status != WithdrawalRequest.Status.PENDING:

            return Response(
                {
                    "error": "Only pending requests can be approved."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        withdraw_request.status = WithdrawalRequest.Status.APPROVED
        withdraw_request.approved_by = request.user
        withdraw_request.approved_at = timezone.now()

        withdraw_request.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
            ]
        )

        return Response(
            {
                "success": True,
                "status": withdraw_request.status,
            }
        )    

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):

        if not request.user.is_staff:

            return Response(
                {
                    "error": "Only admin can pay withdrawal requests."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        withdraw_request = self.get_object()

        if withdraw_request.status != WithdrawalRequest.Status.APPROVED:

            return Response(
                {
                    "error": "Request must be approved first."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if withdraw_request.wallet.balance < withdraw_request.amount:

            return Response(
                {
                    "error": "Insufficient wallet balance."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet = withdraw_request.wallet

        balance_before = wallet.balance

        balance_after = balance_before - withdraw_request.amount

        wallet.balance = balance_after
        wallet.save(update_fields=["balance"])

        transaction = WalletTransaction.objects.create(

            wallet=wallet,

            transaction_type=TransactionType.WITHDRAW,

            amount=withdraw_request.amount,

            balance_before=balance_before,

            balance_after=balance_after,

            description="Withdrawal",

            status=WalletTransaction.TransactionStatus.SUCCESS,

            is_completed=True,

            paid_at=timezone.now(),

        )

        withdraw_request.wallet_transaction = transaction

        withdraw_request.status = WithdrawalRequest.Status.PAID

        withdraw_request.tracking_code = request.data.get(
            "tracking_code",
            "",
        )

        withdraw_request.paid_by = request.user

        withdraw_request.paid_at = timezone.now()

        withdraw_request.save(
            update_fields=[
                "wallet_transaction",
                "status",
                "tracking_code",
                "paid_by",
                "paid_at",
            ]
        )

        if withdraw_request.status == WithdrawalRequest.Status.PAID:

            return Response(
                {
                    "error": "This request has already been paid."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )        

        return Response(
            {
                "success": True,
                "balance": wallet.balance,
                "transaction_id": transaction.id,
            }
        )
    
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):

        withdraw_request = self.get_object()

        if not request.user.is_staff:

            return Response(
                {
                    "error": "Only admin can reject requests."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if withdraw_request.status != WithdrawalRequest.Status.PENDING:

            return Response(
                {
                    "error": "Only pending requests can be rejected."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        withdraw_request.status = WithdrawalRequest.Status.REJECTED

        withdraw_request.reject_reason = request.data.get(
            "reason",
            "",
        )

        withdraw_request.save(
            update_fields=[
                "status",
                "reject_reason",
            ]
        )

        return Response(
            {
                "success": True,
                "status": withdraw_request.status,
            }
        )    

class PaymentCallbackView(APIView):

    permission_classes = []
    authentication_classes = []

    def get(self, request):

        authority = request.GET.get("Authority")
        status_param = request.GET.get("Status")

        if authority is None:

            return Response(
                {
                    "success": False,
                    "message": "Authority not found",
                },
                status=400,
            )

        try:

            gateway_transaction = GatewayTransaction.objects.get(
                authority=authority,
            )

        except GatewayTransaction.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "Transaction not found",
                },
                status=404,
            )

        # ثبت Callback
        GatewayCallback.objects.create(
            transaction=gateway_transaction,
            raw_data=request.GET.dict(),
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        # کاربر پرداخت را لغو کرده است
        if status_param != "OK":

            gateway_transaction.success = False
            gateway_transaction.is_verified = False
            gateway_transaction.save()

            return Response(
                {
                    "success": False,
                    "message": "Payment cancelled.",
                }
            )

        # بررسی درگاه
        gateway_transaction = PaymentGatewayService.verify_payment(
            gateway_transaction,
        )

        if not gateway_transaction.is_verified:

            return Response(
                {
                    "success": False,
                    "message": "Payment verification failed.",
                }
            )

        # شارژ کیف پول
        WalletService.confirm_deposit(
            gateway_transaction.wallet_transaction,
        )

        return Response(
            {
                "success": True,
                "reference": gateway_transaction.ref_id,
            }
        )
    

    