from abc import ABC, abstractmethod


class BaseSmsProvider(ABC):

    @abstractmethod
    def send(
        self,
        mobile: str,
        message: str,
    ):
        """
        باید پیامک را ارسال کند.

        خروجی استاندارد:

        {
            "success": True,
            "message_id": "...",
            "provider": "..."
        }

        یا

        {
            "success": False,
            "error": "..."
        }
        """
        raise NotImplementedError