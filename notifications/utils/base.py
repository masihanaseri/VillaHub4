from abc import ABC, abstractmethod


class BaseNotificationProvider(ABC):

    @abstractmethod
    def send(
        self,
        *,
        receiver,
        title,
        message,
    ):
        pass