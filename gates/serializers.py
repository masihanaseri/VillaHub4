from rest_framework import serializers

from .models import Gate

from .validators import validate_coordinates_pair


class GateSerializer(
    serializers.ModelSerializer,
):

    township_name = serializers.CharField(
        source="township.name",
        read_only=True,
    )

    has_coordinates = serializers.BooleanField(
        read_only=True,
    )

    class Meta:

        model = Gate

        fields = (
            "id",
            "uuid",
            "township",
            "township_name",
            "name",
            "code",
            "description",
            "is_active",
            "latitude",
            "longitude",
            "has_coordinates",
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

    def validate_code(
        self,
        value,
    ):

        return value.strip().upper()

    def validate(
        self,
        attrs,
    ):

        latitude = attrs.get(
            "latitude",
            self.instance.latitude if self.instance else None,
        )

        longitude = attrs.get(
            "longitude",
            self.instance.longitude if self.instance else None,
        )

        validate_coordinates_pair(
            latitude,
            longitude,
        )

        return attrs

    def create(
        self,
        validated_data,
    ):

        from .services import GateService

        request = self.context["request"]

        return GateService.create(
            township=request.user.active_township,
            **validated_data,
        )

    def update(
        self,
        instance,
        validated_data,
    ):

        from .services import GateService

        return GateService.update(
            gate=instance,
            **validated_data,
        )
