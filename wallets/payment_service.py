from django.urls import reverse
from .models import WalletTransaction
from .payment_gateways.factory import GatewayFactory

from .models import (
    PaymentGateway,
    GatewayTransaction,
)


class PaymentGatewayService:

    @staticmethod
    def get_active_gateway():

        gateway = (
            PaymentGateway.objects
            .filter(is_active=True)
            .order_by("priority")
            .first()
        )

        if gateway is None:
            raise Exception(
                "No active payment gateway found."
            )

        return gateway

    @staticmethod
    def get_payment_url(
        gateway,
        authority,
    ):

        if gateway.slug == "zarinpal":

            if gateway.sandbox:

                return (
                    f"https://sandbox.zarinpal.com/pg/StartPay/{authority}"
                )

            return (
                f"https://payment.zarinpal.com/pg/StartPay/{authority}"
            )

        raise Exception(
            f"Payment URL for '{gateway.slug}' is not implemented."
        )

    @staticmethod
    def create_payment(
        wallet_transaction,
        request,
    ):

        if wallet_transaction.status == WalletTransaction.TransactionStatus.SUCCESS:
            raise Exception("This transaction has already been paid.")

        gateway = PaymentGatewayService.get_active_gateway()

        adapter = GatewayFactory.get(
            gateway.slug,
        )

        merchant_id = (
            gateway.sandbox_merchant_id
            if gateway.sandbox
            else gateway.production_merchant_id
        )

        callback_url = request.build_absolute_uri(
            reverse(
                "wallet-payment-callback",
            )
        )

        result = adapter.create_payment(
            merchant_id=merchant_id,
            amount=wallet_transaction.amount,
            callback_url=callback_url,
            sandbox=gateway.sandbox,
            description=f"Wallet Transaction #{wallet_transaction.id}",
        )

        data = result.get("data", {})

        authority = data.get("authority")

        if authority is None:

            raise Exception(
                "Gateway did not return authority."
            )

        gateway_transaction = GatewayTransaction.objects.create(

            wallet=wallet_transaction.wallet,

            invoice=wallet_transaction.invoice,

            gateway=gateway,

            wallet_transaction=wallet_transaction,

            amount=wallet_transaction.amount,

            authority=authority,

            raw_request=result,

        )

        payment_url = PaymentGatewayService.get_payment_url(
            gateway,
            authority,
        )

        return payment_url

    @staticmethod
    def verify_payment(
        gateway_transaction,
    ):

        if gateway_transaction.is_verified:

            return gateway_transaction

        gateway = gateway_transaction.gateway

        adapter = GatewayFactory.get(
            gateway.slug,
        )

        merchant_id = (
            gateway.sandbox_merchant_id
            if gateway.sandbox
            else gateway.production_merchant_id
        )

        result = adapter.verify_payment(
            merchant_id=merchant_id,
            authority=gateway_transaction.authority,
            amount=gateway_transaction.amount,
            sandbox=gateway.sandbox,
        )

        gateway_transaction.raw_response = result

        data = result.get("data", {})

        if data.get("code") == 100:

            gateway_transaction.success = True

            gateway_transaction.is_verified = True

            gateway_transaction.ref_id = str(
                data.get("ref_id")
            )

            wallet_transaction = gateway_transaction.wallet_transaction

            wallet_transaction.gateway_name = gateway.slug
            wallet_transaction.gateway_ref_id = gateway_transaction.ref_id
            wallet_transaction.authority = gateway_transaction.authority
            wallet_transaction.save(
                update_fields=[
                    "gateway_name",
                    "gateway_ref_id",
                    "authority",
                ]
            )            

        else:

            gateway_transaction.success = False

            gateway_transaction.is_verified = False

        gateway_transaction.save()

        return gateway_transaction