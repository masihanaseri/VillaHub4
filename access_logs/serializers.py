from rest_framework import serializers

from .models import AccessLog


class AccessLogSerializer(
    serializers.ModelSerializer,
):

    gate_name = serializers.CharField(
        source="gate.name",
        read_only=True,
    )

    guard_name = serializers.SerializerMethodField()

    visitor_name = serializers.CharField(
        source="visitor.full_name",
        read_only=True,
        default=None,
    )

    subject_display = serializers.CharField(
        read_only=True,
    )

    direction_display = serializers.CharField(
        source="get_direction_display",
        read_only=True,
    )

    access_method_display = serializers.CharField(
        source="get_access_method_display",
        read_only=True,
    )

    class Meta:

        model = AccessLog

        fields = (
            "id",
            "uuid",
            "township",
            "gate",
            "gate_name",
            "guard",
            "guard_name",
            "visitor",
            "visitor_name",
            "residence",
            "subject_display",
            "direction",
            "direction_display",
            "access_method",
            "access_method_display",
            "plate_number",
            "occurred_at",
            "notes",
            "created_at",
        )

        read_only_fields = (
            "id",
            "uuid",
            "township",
            "occurred_at",
            "created_at",
        )

    def get_guard_name(self, obj):

        if obj.guard_id is None:

            return None

        return str(obj.guard)

    def create(self, validated_data):

        from .services import AccessLogService

        return AccessLogService.record(
            gate=validated_data["gate"],
            direction=validated_data["direction"],
            guard=validated_data.get("guard"),
            visitor=validated_data.get("visitor"),
            residence=validated_data.get("residence"),
            access_method=validated_data.get(
                "access_method",
                AccessLog.AccessMethod.MANUAL,
            ),
            plate_number=validated_data.get("plate_number", ""),
            notes=validated_data.get("notes", ""),
        )

    def update(self, instance, validated_data):

        raise serializers.ValidationError(
            "رویدادهای تردد پس از ثبت غیرقابل ویرایش هستند.",
        )
