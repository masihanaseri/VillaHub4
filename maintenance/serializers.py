from rest_framework import serializers

from .models import (
    MaintenanceRequest,
    MaintenanceAttachment,
    MaintenanceComment,
    MaintenanceHistory,
)


class MaintenanceAttachmentSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = MaintenanceAttachment

        fields = "__all__"

        read_only_fields = (
            "id",
            "uuid",
            "created_at",
            "updated_at",
        )


class MaintenanceCommentSerializer(
    serializers.ModelSerializer
):

    user_name = serializers.CharField(
        source="user.get_full_name",
        read_only=True,
    )

    class Meta:

        model = MaintenanceComment

        fields = "__all__"

        read_only_fields = (
            "id",
            "uuid",
            "created_at",
            "updated_at",
        )


class MaintenanceHistorySerializer(
    serializers.ModelSerializer
):

    user_name = serializers.CharField(
        source="user.get_full_name",
        read_only=True,
    )

    class Meta:

        model = MaintenanceHistory

        fields = "__all__"

        read_only_fields = (
            "id",
            "uuid",
            "created_at",
            "updated_at",
        )


class MaintenanceRequestSerializer(
    serializers.ModelSerializer
):

    attachments = MaintenanceAttachmentSerializer(
        many=True,
        read_only=True,
    )

    comments = MaintenanceCommentSerializer(
        many=True,
        read_only=True,
    )

    history = MaintenanceHistorySerializer(
        many=True,
        read_only=True,
    )

    created_by_name = serializers.CharField(
        source="created_by.get_full_name",
        read_only=True,
    )

    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name",
        read_only=True,
    )

    township_name = serializers.CharField(
        source="township.name",
        read_only=True,
    )

    villa_name = serializers.CharField(
        source="villa.__str__",
        read_only=True,
    )

    class Meta:

        model = MaintenanceRequest

        fields = "__all__"

        read_only_fields = (
            "id",
            "uuid",
            "created_at",
            "updated_at",
            "created_by",
        )