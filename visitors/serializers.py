from rest_framework import serializers

from .models import (
    Visitor,
    VisitorVehicle,
    VisitorLog,
)

class VisitorVehicleSerializer(
    serializers.ModelSerializer,
):

    class Meta:

        model = VisitorVehicle

        fields = "__all__"

        read_only_fields = (

            "id",

            "uuid",

            "created_at",

            "updated_at",

        )
class VisitorLogSerializer(
    serializers.ModelSerializer,
):

    user_name = serializers.CharField(

        source="user.get_full_name",

        read_only=True,

    )

    class Meta:

        model = VisitorLog

        fields = "__all__"

        read_only_fields = (

            "id",

            "uuid",

            "created_at",

            "updated_at",

        )

class VisitorSerializer(
    serializers.ModelSerializer,
):

    residence_name = serializers.CharField(

        source="residence.user.get_full_name",

        read_only=True,

    )

    villa_code = serializers.CharField(

        source="residence.villa.code",

        read_only=True,

    )

    created_by_name = serializers.CharField(

        source="created_by.get_full_name",

        read_only=True,

    )

    approved_by_name = serializers.CharField(

        source="approved_by.get_full_name",

        read_only=True,

        default="",

    )

    status_display = serializers.CharField(

        source="get_status_display",

        read_only=True,

    )

    vehicles = VisitorVehicleSerializer(

        many=True,

        read_only=True,

    )

    logs = VisitorLogSerializer(

        many=True,

        read_only=True,

    )

    class Meta:

        model = Visitor

        fields = (

            "id",

            "uuid",

            "township",

            "residence",

            "residence_name",

            "villa_code",

            "created_by",

            "created_by_name",

            "visitor_type",

            "full_name",

            "national_code",

            "mobile",

            "adult_count",

            "child_count",

            "valid_from",

            "valid_until",

            "status",

            "status_display",

            "purpose",

            "notes",

            "approved_by",

            "approved_by_name",

            "approved_at",

            "checked_in_at",

            "checked_out_at",

            "vehicles",

            "logs",

            "created_at",

            "updated_at",

        )

        read_only_fields = (

            "id",

            "uuid",

            "township",

            "created_by",

            "status",

            "approved_by",

            "approved_at",

            "checked_in_at",

            "checked_out_at",

            "created_at",

            "updated_at",

        )

    def validate(

        self,

        attrs,

    ):

        valid_from = attrs.get(

            "valid_from",

            self.instance.valid_from if self.instance else None,

        )

        valid_until = attrs.get(

            "valid_until",

            self.instance.valid_until if self.instance else None,

        )

        if (

            valid_from

            and

            valid_until

            and

            valid_until

            <=

            valid_from

        ):

            raise serializers.ValidationError(

                "زمان پایان باید بعد از زمان شروع باشد."

            )

        return attrs
    
    def create(

        self,

        validated_data,

    ):

        from .services import VisitorService

        request = self.context["request"]

        return VisitorService.create(

            created_by=request.user,

            **validated_data,

        )

    def update(

        self,

        instance,

        validated_data,

    ):

        raise serializers.ValidationError(

            "ویرایش مستقیم مجاز نیست."

        )
