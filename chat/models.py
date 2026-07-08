from django.conf import settings
from django.db import models

from core.models import BaseModel
from .managers import ConversationManager


class Conversation(BaseModel):

    class ConversationType(models.TextChoices):

        PRIVATE = "PRIVATE", "خصوصی"
        GROUP = "GROUP", "گروهی"
        TOWNSHIP = "TOWNSHIP", "شهرک"

    conversation_type = models.CharField(
        max_length=20,
        choices=ConversationType.choices,
        default=ConversationType.PRIVATE,
    )

    township = models.ForeignKey(
        "townships.Township",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="conversations",
    )

    title = models.CharField(
        max_length=200,
        blank=True,
    )

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="conversations",
    )

    is_archived = models.BooleanField(
        default=False,
    )  

    is_muted = models.BooleanField(
        default=False,
    )

    is_starred = models.BooleanField(
        default=False,
    )

    pinned_message = models.ForeignKey(
        "chat.Message",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )      

    objects = ConversationManager()

    class Meta:

        db_table = "chat_conversations"

        ordering = [
            "-updated_at",
        ]

    def __str__(self):

        return self.title or f"Conversation {self.id}"


class Message(BaseModel):

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    text = models.TextField()

    is_edited = models.BooleanField(
        default=False,
    )

    is_deleted = models.BooleanField(
        default=False,
    )

    is_seen = models.BooleanField(
        default=False,
    )

    seen_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    attachment = models.FileField(
        upload_to="chat/",
        null=True,
        blank=True,
    )

    seen_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="seen_messages",
    )

    deleted_for_everyone = models.BooleanField(
        default=False,
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )    

    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
    )

    is_pinned = models.BooleanField(
        default=False,
    )

    pinned_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    pinned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pinned_messages",
    )

    class Meta:

        db_table = "chat_messages"

        ordering = [
            "created_at",
        ]

    def __str__(self):

        return self.text[:50]

class MessageReaction(BaseModel):

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="reactions",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    emoji = models.CharField(
        max_length=20,
    )

    class Meta:

        unique_together = (

            "message",

            "user",

        )