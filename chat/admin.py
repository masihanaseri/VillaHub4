from django.contrib import admin

from .models import Conversation
from .models import Message


@admin.register(

    Conversation,

)

class ConversationAdmin(

    admin.ModelAdmin,

):

    list_display = (

        "id",

        "conversation_type",

        "created_at",

    )

    filter_horizontal = (

        "members",

    )


@admin.register(

    Message,

)

class MessageAdmin(

    admin.ModelAdmin,

):

    list_display = (

        "id",

        "sender",

        "conversation",

        "created_at",

    )

    search_fields = (

        "text",

    )