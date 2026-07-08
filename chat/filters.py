import django_filters

from .models import Conversation


class ConversationFilter(

    django_filters.FilterSet,

):

    class Meta:

        model = Conversation

        fields = [

            "conversation_type",

        ]