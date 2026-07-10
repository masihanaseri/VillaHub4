from abc import ABC, abstractmethod


class BasePaymentGateway(ABC):

    @abstractmethod
    def create_payment(
        self,
        merchant_id,
        amount,
        callback_url,
        sandbox=False,
        description="",
    ):
        """
        Create payment request.
        Must return gateway response.
        """
        raise NotImplementedError

    @abstractmethod
    def verify_payment(
        self,
        merchant_id,
        authority,
        amount,
        sandbox=False,
    ):
        """
        Verify payment.
        Must return gateway response.
        """
        raise NotImplementedError

    @abstractmethod
    def get_payment_url(
        self,
        authority,
        sandbox=False,
    ):
        """
        Return redirect URL.
        """
        raise NotImplementedError