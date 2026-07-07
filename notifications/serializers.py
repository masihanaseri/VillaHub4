from rest_framework import serializers

from .models import (
    Notification,
    NotificationLog,
)

class NotificationLogSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = NotificationLog

        fields = "__all__"

        read_only_fields = (

            "id",

            "uuid",

            "created_at",

            "updated_at",

        )

class NotificationSerializer(
    serializers.ModelSerializer
):

    logs = NotificationLogSerializer(

        many=True,

        read_only=True,

    )

    class Meta:

        model = Notification

        fields = "__all__"

        read_only_fields = (

            "id",

            "uuid",

            "created_at",

            "updated_at",

        )
class NotificationCreateSerializer(serializers.ModelSerializer):

    class Meta:

        model = Notification

        fields = [

            "title",

            "message",

            "notification_type",

            "priority",

            "township",

            "is_global",

        ]