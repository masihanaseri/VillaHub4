from .base import BaseNotificationProvider


class PushProvider(BaseNotificationProvider):

    def send(
        self,
        *,
        receiver,
        title,
        message,
    ):

        return {

            "success": True,

            "provider_message_id": "",

            "error": "",

        }