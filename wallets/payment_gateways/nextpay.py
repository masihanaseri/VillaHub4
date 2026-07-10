from .base import BasePaymentGateway


class NextPayGateway(BasePaymentGateway):

    def get_base_url(
        self,
        sandbox=False,
    ):
        raise NotImplementedError(
            "NextPay gateway has not been implemented yet."
        )

    def get_payment_url(
        self,
        authority,
        sandbox=False,
    ):
        raise NotImplementedError(
            "NextPay gateway has not been implemented yet."
        )

    def create_payment(
        self,
        merchant_id,
        amount,
        callback_url,
        sandbox=False,
        description="",
    ):
        raise NotImplementedError(
            "NextPay gateway has not been implemented yet."
        )

    def verify_payment(
        self,
        merchant_id,
        authority,
        amount,
        sandbox=False,
    ):
        raise NotImplementedError(
            "NextPay gateway has not been implemented yet."
        )