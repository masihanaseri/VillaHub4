from .base import BaseNotificationProvider


class EmailProvider(BaseNotificationProvider):

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