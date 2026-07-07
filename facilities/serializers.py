from rest_framework import serializers

from .models import Facility


class FacilitySerializer(serializers.ModelSerializer):
    """
    Serializer مربوط به امکانات شهرک
    """

    township_name = serializers.CharField(
        source="township.name",
        read_only=True,
    )

    is_free = serializers.SerializerMethodField()

    class Meta:

        model = Facility

        fields = (
            "id",
            "uuid",

            "code",
            "name",
            "description",

            "capacity",

            "reservation_policy",
            "pricing_policy",
            "booking_mode",

            "reservation_unit",
            "reservation_interval",

            "requires_approval",
            "allow_cancellation",
            "cancellation_deadline_hours",

            "max_reservation_duration",

            "available_from",
            "available_until",

            "max_parallel_reservations",

            "minimum_guest_count",
            "maximum_guest_count",

            "allow_waiting_list",

            "is_paid",
            "is_free",
            "price",
            "deposit",
            "minimum_charge",
            "tax_percent",
            "discount_percent",

            "is_active",

            "township",
            "township_name",

            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "uuid",

            "township",
            "township_name",

            "created_at",
            "updated_at",
        )

    def get_is_free(self, obj):

        return not obj.is_paid

    # ----------------------------

    def validate_code(self, value):

        value = value.strip().upper()

        if len(value) < 2:

            raise serializers.ValidationError(
                "کد باید حداقل دو کاراکتر باشد."
            )

        return value

    def validate_name(self, value):

        value = value.strip()

        if len(value) < 2:

            raise serializers.ValidationError(
                "نام امکانات معتبر نیست."
            )

        return value

    def validate_capacity(self, value):

        if value <= 0:

            raise serializers.ValidationError(
                "ظرفیت باید بزرگتر از صفر باشد."
            )

        return value

    def validate_price(self, value):

        if value < 0:

            raise serializers.ValidationError(
                "قیمت نمی‌تواند منفی باشد."
            )

        return value

    def validate_deposit(self, value):

        if value < 0:

            raise serializers.ValidationError(
                "ودیعه نمی‌تواند منفی باشد."
            )

        return value

    def validate_max_parallel_reservations(self, value):

        if value <= 0:

            raise serializers.ValidationError(
                "حداقل باید یک رزرو همزمان مجاز باشد."
            )

        return value

    def validate_max_reservation_duration(self, value):

        if value <= 0:

            raise serializers.ValidationError(
                "مدت رزرو باید بیشتر از صفر باشد."
            )

        return value

    def validate_minimum_guest_count(self, value):

        if value <= 0:

            raise serializers.ValidationError(
                "حداقل تعداد نفرات باید بیشتر از صفر باشد."
            )

        return value

    def validate_maximum_guest_count(self, value):

        if value <= 0:

            raise serializers.ValidationError(
                "حداکثر تعداد نفرات باید بیشتر از صفر باشد."
            )

        return value

    def validate_minimum_charge(self, value):

        if value < 0:

            raise serializers.ValidationError(
                "حداقل مبلغ نمی‌تواند منفی باشد."
            )

        return value

    def validate_tax_percent(self, value):

        if value < 0 or value > 100:

            raise serializers.ValidationError(
                "درصد مالیات باید بین ۰ تا ۱۰۰ باشد."
            )

        return value

    def validate_discount_percent(self, value):

        if value < 0 or value > 100:

            raise serializers.ValidationError(
                "درصد تخفیف باید بین ۰ تا ۱۰۰ باشد."
            )

        return value

    # ----------------------------

    def validate(self, attrs):

        township = self.context["township"]

        code = attrs["code"]

        queryset = Facility.objects.filter(
            township=township,
            code=code,
        )

        if self.instance:

            queryset = queryset.exclude(
                pk=self.instance.pk,
            )

        if queryset.exists():

            raise serializers.ValidationError(
                {
                    "code":
                    "این کد قبلاً ثبت شده است."
                }
            )

        is_paid = attrs.get(
            "is_paid",
            self.instance.is_paid if self.instance else False,
        )

        price = attrs.get(
            "price",
            self.instance.price if self.instance else 0,
        )

        if is_paid:

            if price <= 0:

                raise serializers.ValidationError(
                    {
                        "price":
                        "برای امکانات پولی قیمت باید بیشتر از صفر باشد."
                    }
                )

        else:

            attrs["price"] = 0
            attrs["deposit"] = 0

        available_from = attrs.get("available_from")

        available_until = attrs.get("available_until")

        if available_from and available_until:

            if available_from >= available_until:

                raise serializers.ValidationError(
                    {
                        "available_until":
                        "ساعت پایان باید بعد از ساعت شروع باشد."
                    }
                )

        policy = attrs.get(
            "reservation_policy",
            self.instance.reservation_policy
            if self.instance
            else Facility.ReservationPolicy.EXCLUSIVE,
        )

        if (
            policy
            ==
            Facility.ReservationPolicy.EXCLUSIVE
        ):

            attrs["max_parallel_reservations"] = 1

        minimum_guest_count = attrs.get(
            "minimum_guest_count",
            self.instance.minimum_guest_count
            if self.instance
            else 1,
        )

        maximum_guest_count = attrs.get(
            "maximum_guest_count",
            self.instance.maximum_guest_count
            if self.instance
            else 999,
        )

        if minimum_guest_count > maximum_guest_count:

            raise serializers.ValidationError(
                {
                    "maximum_guest_count":
                    "حداکثر تعداد نفرات باید بزرگتر یا مساوی حداقل باشد."
                }
            )

        return attrs

    # ----------------------------

    def create(self, validated_data):

        township = self.context["township"]

        return Facility.objects.create(
            township=township,
            **validated_data,
        )

    def update(self, instance, validated_data):

        for attr, value in validated_data.items():

            setattr(
                instance,
                attr,
                value,
            )

        instance.save()

        return instance