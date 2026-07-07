from rest_framework import serializers

from .models import (
    AccessPass,
    AccessLog,
)


class AccessLogSerializer(
    serializers.ModelSerializer,
):
    """
    سریالایزر فقط-خواندنی برای دفترچه ممیزی تردد. ثبت رویداد همیشه از
    طریق AccessControlService (توسط actionهای AccessPassViewSet) انجام
    می‌شود، نه با POST مستقیم به این سریالایزر.
    """

    gate_name = serializers.CharField(
        source="gate.name",
        read_only=True,
    )

    guard_name = serializers.SerializerMethodField()

    visitor_name = serializers.CharField(
        source="access_pass.visitor.full_name",
        read_only=True,
    )

    action_display = serializers.CharField(
        source="get_action_display",
        read_only=True,
    )

    class Meta:

        model = AccessLog

        fields = (
            "id",
            "uuid",
            "township",
            "access_pass",
            "visitor_name",
            "gate",
            "gate_name",
            "guard",
            "guard_name",
            "action",
            "action_display",
            "device",
            "latitude",
            "longitude",
            "ip_address",
            "notes",
            "created_at",
            "updated_at",
        )

        read_only_fields = fields

    def get_guard_name(self, obj):

        if obj.guard_id is None:

            return None

        return str(obj.guard)


class AccessLogInlineSerializer(
    serializers.ModelSerializer,
):
    """
    نسخه فشرده AccessLog برای نمایش تو در تو داخل AccessPassSerializer.
    """

    action_display = serializers.CharField(
        source="get_action_display",
        read_only=True,
    )

    gate_name = serializers.CharField(
        source="gate.name",
        read_only=True,
    )

    class Meta:

        model = AccessLog

        fields = (
            "id",
            "uuid",
            "gate",
            "gate_name",
            "guard",
            "action",
            "action_display",
            "device",
            "created_at",
        )

        read_only_fields = fields


class AccessPassSerializer(
    serializers.ModelSerializer,
):

    visitor_name = serializers.CharField(
        source="visitor.full_name",
        read_only=True,
    )

    visitor_mobile = serializers.CharField(
        source="visitor.mobile",
        read_only=True,
    )

    gate_name = serializers.CharField(
        source="gate.name",
        read_only=True,
        default=None,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    created_by_name = serializers.SerializerMethodField()

    approved_by_name = serializers.SerializerMethodField()

    is_valid = serializers.BooleanField(
        read_only=True,
    )

    is_expired = serializers.BooleanField(
        read_only=True,
    )

    is_active = serializers.BooleanField(
        read_only=True,
    )

    class Meta:

        model = AccessPass

        fields = (
            "id",
            "uuid",
            "township",
            "visitor",
            "visitor_name",
            "visitor_mobile",
            "gate",
            "gate_name",
            "qr_token",
            "valid_from",
            "valid_until",
            "status",
            "status_display",
            "created_by",
            "created_by_name",
            "approved_by",
            "approved_by_name",
            "approved_at",
            "checked_in_at",
            "checked_out_at",
            "notes",
            "is_valid",
            "is_expired",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "uuid",
            "township",
            "qr_token",
            "status",
            "created_by",
            "approved_by",
            "approved_at",
            "checked_in_at",
            "checked_out_at",
            "is_valid",
            "is_expired",
            "is_active",
            "created_at",
            "updated_at",
        )

    def get_created_by_name(self, obj):

        if obj.created_by_id is None:

            return None

        return obj.created_by.get_full_name() or obj.created_by.username

    def get_approved_by_name(self, obj):

        if obj.approved_by_id is None:

            return None

        return obj.approved_by.get_full_name() or obj.approved_by.username

    def validate(self, attrs):

        valid_from = attrs.get(
            "valid_from",
            self.instance.valid_from if self.instance else None,
        )

        valid_until = attrs.get(
            "valid_until",
            self.instance.valid_until if self.instance else None,
        )

        if valid_from and valid_until and valid_until <= valid_from:

            raise serializers.ValidationError(
                "زمان پایان اعتبار باید بعد از زمان شروع باشد.",
            )

        return attrs

    def create(self, validated_data):

        from .services import AccessControlService

        request = self.context["request"]

        return AccessControlService.create_access_pass(
            visitor=validated_data["visitor"],
            created_by=request.user,
            valid_from=validated_data["valid_from"],
            valid_until=validated_data["valid_until"],
            gate=validated_data.get("gate"),
            notes=validated_data.get("notes", ""),
        )

    def update(self, instance, validated_data):

        if instance.status != AccessPass.Status.PENDING:

            raise serializers.ValidationError(
                "فقط کارت‌های در انتظار تایید قابل ویرایش هستند.",
            )

        for field, value in validated_data.items():

            setattr(instance, field, value)

        instance.save()

        return instance


class AccessPassDetailSerializer(
    AccessPassSerializer,
):
    """
    نسخه کامل AccessPass شامل تاریخچه رویدادهای تردد.
    """

    logs = AccessLogInlineSerializer(
        many=True,
        read_only=True,
    )

    class Meta(
        AccessPassSerializer.Meta,
    ):

        fields = (
            AccessPassSerializer.Meta.fields
            + (
                "logs",
            )
        )

