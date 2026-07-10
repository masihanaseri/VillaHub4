import requests

from .base import BasePaymentGateway


class ZarinPalGateway(BasePaymentGateway):

    SANDBOX_URL = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"

    PRODUCTION_URL = "https://payment.zarinpal.com/pg/v4/payment/request.json"

    SANDBOX_VERIFY = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"

    PRODUCTION_VERIFY = "https://payment.zarinpal.com/pg/v4/payment/verify.json"

    HEADERS = {
        "accept": "application/json",
        "content-type": "application/json",
    }

    TIMEOUT = 30

    def get_request_url(self, sandbox):

        return self.SANDBOX_URL if sandbox else self.PRODUCTION_URL

    def get_verify_url(self, sandbox):

        return self.SANDBOX_VERIFY if sandbox else self.PRODUCTION_VERIFY

    def get_payment_url(self, authority, sandbox=False):

        if sandbox:
            return f"https://sandbox.zarinpal.com/pg/StartPay/{authority}"

        return f"https://payment.zarinpal.com/pg/StartPay/{authority}"

    def create_payment(
        self,
        merchant_id,
        amount,
        callback_url,
        sandbox=False,
        description="",
    ):

        payload = {
            "merchant_id": merchant_id,
            "amount": int(amount),
            "callback_url": callback_url,
            "description": description,
        }

        response = requests.post(
            self.get_request_url(sandbox),
            json=payload,
            headers=self.HEADERS,
            timeout=self.TIMEOUT,
        )

        response.raise_for_status()

        return response.json()

    def verify_payment(
            self,
            merchant_id,
            authority,
            amount,
            sandbox=False,
        ):

            payload = {
                "merchant_id": merchant_id,
                "authority": authority,
                "amount": int(amount),
            }

            response = requests.post(
                        self.get_verify_url(sandbox),
                        json=payload,
                        headers=self.HEADERS,
                        timeout=self.TIMEOUT,
                    )

            if not response.ok:
                raise Exception(
                    f"ZarinPal error {response.status_code}: {response.text}"
                )

            return response.json()