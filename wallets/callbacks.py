from django.db import transaction

from wallets.models import (
    GatewayCallback,
)

from wallets.payment_service import (
    PaymentGatewayService,
)

from wallets.services import (
    WalletService,
)


class CallbackService:

    @staticmethod
    @transaction.atomic
    def process(
        gateway_transaction,
        request,
    ):
        """
        پردازش Callback درگاه پرداخت

        مراحل:
        1- جلوگیری از Verify دوباره
        2- Verify از درگاه
        3- ثبت Callback
        4- در صورت موفق بودن:
              - اگر پرداخت فاکتور باشد → فاکتور Paid شود.
              - اگر شارژ کیف پول باشد → کیف پول شارژ شود.
        """

        # جلوگیری از Verify تکراری
        if gateway_transaction.is_verified:
            return gateway_transaction

        # Verify از درگاه
        verify = PaymentGatewayService.verify_payment(
            gateway_transaction,
        )

        # ثبت Callback
# ثبت Callback
        GatewayCallback.objects.create(
            raw_data={
                "gateway_transaction_id": gateway_transaction.id,
                "authority": request.GET.get(
                    "Authority",
                    "",
                ),
                "status": request.GET.get(
                    "Status",
                    "",
                ),
                "query_params": dict(request.GET),
            },
            ip_address=request.META.get(
                "REMOTE_ADDR",
                "0.0.0.0",
            ),
            user_agent=request.META.get(
                "HTTP_USER_AGENT",
                "",
            ),
        )

        # اگر Verify ناموفق بود
        if not verify.is_verified:
            return verify

        wallet_transaction = (
            gateway_transaction.wallet_transaction
        )

        # -------------------------
        # پرداخت فاکتور
        # -------------------------

        if (
            hasattr(wallet_transaction, "invoice")
            and wallet_transaction.invoice
        ):

            from billing.payment_service import (
                InvoicePaymentService,
            )

            InvoicePaymentService.pay_from_wallet(
                invoice=wallet_transaction.invoice,
                wallet=wallet_transaction.wallet,
            )

        # -------------------------
        # شارژ کیف پول
        # -------------------------

        else:

            WalletService.deposit(
                wallet=wallet_transaction.wallet,
                amount=gateway_transaction.amount,
                description="Online Wallet Charge",
                reference=verify.ref_id,
            )

        # تکمیل تراکنش
        wallet_transaction.is_completed = True
        wallet_transaction.save()

        return verify