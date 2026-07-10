from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets
from .payment_service import PaymentGatewayService


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

from rest_framework.views import APIView


from rest_framework.views import APIView


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