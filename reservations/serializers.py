from rest_framework import serializers


from .models import (
    Reservation,
    ReservationPayment,
    ReservationLog,
    ReservationSlot,
)


def _display_name(user):

    if user is None:

        return ""

    return (
        user.get_full_name()
        or
        user.username
    )


class ReservationSlotSerializer(serializers.ModelSerializer):

    class Meta:

        model = ReservationSlot

        fields = (
            "id",
            "uuid",
            "facility",
            "title",
            "start_time",
            "end_time",
            "capacity",
            "is_active",
            "sort_order",
        )

        read_only_fields = (
            "id",
            "uuid",
        )

    def validate(self, attrs):

        start_time = attrs.get(
            "start_time",
            self.instance.start_time if self.instance else None,
        )

        end_time = attrs.get(
            "end_time",
            self.instance.end_time if self.instance else None,
        )

        if start_time and end_time and end_time <= start_time:

            raise serializers.ValidationError(
                "زمان پایان سانس باید بعد از زمان شروع باشد."
            )

        return attrs


class ReservationPaymentSerializer(serializers.ModelSerializer):

    created_by_name = serializers.SerializerMethodField()

    def get_created_by_name(self, obj):

        return _display_name(obj.created_by)

    class Meta:

        model = ReservationPayment

        fields = "__all__"

        read_only_fields = (
            "id",
            "uuid",
            "created_at",
            "updated_at",
        )

class ReservationLogSerializer(serializers.ModelSerializer):

    user_name = serializers.SerializerMethodField()

    def get_user_name(self, obj):

        return _display_name(obj.user)

    class Meta:

        model = ReservationLog

        fields = "__all__"

        read_only_fields = (
            "id",
            "uuid",
            "created_at",
            "updated_at",
        ) 


class ReservationSerializer(serializers.ModelSerializer):





    reservation_status_display = serializers.CharField(
        source="get_reservation_status_display",
        read_only=True,
    )

    payment_status_display = serializers.CharField(
        source="get_payment_status_display",
        read_only=True,
    )

    payments = ReservationPaymentSerializer(
        many=True,
        read_only=True,
    )

    logs = ReservationLogSerializer(
        many=True,
        read_only=True,
    )

    facility_name = serializers.CharField(
        source="facility.name",
        read_only=True,
    )

    villa_code = serializers.CharField(
        source="residence.villa.code",
        read_only=True,
    )

    resident_name = serializers.SerializerMethodField()

    created_by_name = serializers.SerializerMethodField()

    def get_resident_name(self, obj):

        return _display_name(obj.residence.user)

    def get_created_by_name(self, obj):

        return _display_name(obj.created_by)

    class Meta:

        model = Reservation

        fields = (
            "id",
            "uuid",
            "reservation_number",
            "facility",
            "facility_name",
            "residence",
            "villa_code",
            "start_datetime",
            "end_datetime",
            "guest_count",
            "reservation_status",
            "reservation_status_display",
            "payment_status",
            "payment_status_display",
            "price_snapshot",
            "deposit_snapshot",
            "total_price",
            "notes",
            "facility_name",

            "villa_code",

            "resident_name",

            "created_by_name",

            "payments",

            "logs",            
            
            "slot",

            "paid_amount",

            "remaining_amount",

            "approved_by",

            "approved_at",

            "cancelled_by",

            "cancelled_at",

            "checked_in_at",

            "checked_out_at",

            "admin_note",

            "cancel_reason",
            "created_at",
            "updated_at",

        )

        read_only_fields = (
            "id",
            "uuid",
            "reservation_number",
            "reservation_status",
            "payment_status",
            "price_snapshot",
            "deposit_snapshot",
            "total_price",
            "created_at",
            "updated_at",
        )

        extra_kwargs = {
            # در حالت رزرو سانسی (SLOT) زمان پایان توسط
            # ReservationService از روی سانس محاسبه می‌شود.
            "end_datetime": {
                "required": False,
            },
        }

    def validate_guest_count(self, value):

        if value <= 0:

            raise serializers.ValidationError(
                "تعداد افراد باید بیشتر از صفر باشد."
            )

        return value


    
    def validate(self, attrs):

        start = attrs.get(
            "start_datetime",
            self.instance.start_datetime if self.instance else None,
        )

        end = attrs.get(
            "end_datetime",
            self.instance.end_datetime if self.instance else None,
        )

        if start and end and end <= start:

            raise serializers.ValidationError(
                "زمان پایان باید بعد از زمان شروع باشد."
            )

        return attrs
    
    def create(self, validated_data):

        from .services import ReservationService

        request = self.context["request"]

        return ReservationService.create_reservation(

            created_by=request.user,

            **validated_data,

        )
    def update(
        self,
        instance,
        validated_data,
    ):

        raise serializers.ValidationError(
            "ویرایش مستقیم رزرو مجاز نیست."
        )    
