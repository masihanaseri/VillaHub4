from django.db import transaction

from .models import Conversation
from .models import Message


class ChatService:

    @staticmethod
    @transaction.atomic
    def send_message(

        sender,

        conversation,

        text,

    ):

        message = Message.objects.create(

            conversation=conversation,

            sender=sender,

            text=text,

        )

        return message