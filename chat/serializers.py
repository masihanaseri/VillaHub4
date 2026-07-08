from rest_framework import serializers

from .models import Conversation
from .models import Message


class MessageSerializer(

    serializers.ModelSerializer,

):

    sender_name = serializers.CharField(

        source="sender.get_full_name",

        read_only=True,

    )

    class Meta:

        model = Message

        fields = "__all__"


class ConversationSerializer(

    serializers.ModelSerializer,

):

    messages = MessageSerializer(

        many=True,

        read_only=True,

    )

    class Meta:

        model = Conversation

        fields = "__all__"