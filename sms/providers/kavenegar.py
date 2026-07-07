from .base import BaseSmsProvider


class KavenegarProvider(BaseSmsProvider):

    def send(
        self,
        mobile,
        message,
    ):

        return {

            "success": True,

            "provider": "kavenegar",

            "message_id": "TEST123456",

        }