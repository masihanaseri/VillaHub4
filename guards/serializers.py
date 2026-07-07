from rest_framework import serializers

from gates.models import Gate

from .models import (
    Guard,
    GuardLog,
    GuardShift,
)


class GuardShiftSerializer(
    serializers.ModelSerializer,
):

    duration_seconds = serializers.SerializerMethodField()

    class Meta:

        model = GuardShift

        fields = (
            "id",
            "uuid",
            "guard",
            "started_at",
            "ended_at",
            "duration_seconds",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "uuid",
            "guard",
            "started_at",
            "ended_at",
            "created_at",
            "updated_at",
        )

    def get_duration_seconds(self, obj):

        duration = obj.duration

        if duration is None:

            return None

        return int(duration.total_seconds())


class GuardLogSerializer(
    serializers.ModelSerializer,
):

    performed_by_name = serializers.CharField(
        source="performed_by.get_full_name",
        read_only=True,
        default="",
    )

    action_display = serializers.CharField(
        source="get_action_display",
        read_only=True,
    )

    class Meta:

        model = GuardLog

        fields = (
            "id",
            "uuid",
            "guard",
            "action",
            "action_display",
            "performed_by",
            "performed_by_name",
            "description",
            "created_at",
        )

        read_only_fields = fields


class GuardSerializer(
    serializers.ModelSerializer,
):

    user_name = serializers.SerializerMethodField()

    township_name = serializers.CharField(
        source="township.name",
        read_only=True,
    )

    shift_display = serializers.CharField(
        source="get_shift_display",
        read_only=True,
    )

    gates = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Gate.objects.all(),
        required=False,
    )

    has_active_shift = serializers.BooleanField(
        read_only=True,
    )

    shifts = GuardShiftSerializer(
        many=True,
        read_only=True,
    )

    logs = GuardLogSerializer(
        many=True,
        read_only=True,
    )

    class Meta:

        model = Guard

        fields = (
            "id",
            "uuid",
            "township",
            "township_name",
            "user",
            "user_name",
            "gates",
            "employee_code",
            "phone",
            "shift",
            "shift_display",
            "is_active",
            "has_active_shift",
            "hired_at",
            "notes",
            "shifts",
            "logs",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "uuid",
            "township",
            "is_active",
            "created_at",
            "updated_at",
        )

    def get_user_name(self, obj):

        return obj.user.get_full_name() or obj.user.username

    def validate_gates(self, value):

        request = self.context.get("request")

        township = getattr(request.user, "active_township", None) if request else None

        if township is None:

            return value

        invalid_gates = [
            gate.code for gate in value if gate.township_id != township.id
        ]

        if invalid_gates:

            raise serializers.ValidationError(
                f"درب‌های زیر متعلق به شهرک فعال شما نیستند: {', '.join(invalid_gates)}",
            )

        return value

    def create(self, validated_data):

        gates = validated_data.pop("gates", [])

        request = self.context["request"]

        validated_data["township"] = request.user.active_township

        guard = Guard.objects.create(**validated_data)

        if gates:

            guard.gates.set(gates)

        return guard

    def update(self, instance, validated_data):

        gates = validated_data.pop("gates", None)

        for field_name, value in validated_data.items():

            setattr(instance, field_name, value)

        instance.save()

        if gates is not None:

            instance.gates.set(gates)

        return instance
