from rest_framework import serializers

from accounts.models import Membership

from .models import Villa, Residence

from datetime import date

# =========================
# Villa Serializer
# =========================
class VillaSerializer(serializers.ModelSerializer):

    township_name = serializers.CharField(
        source="township.name",
        read_only=True,
    )

    class Meta:
        model = Villa

        fields = (
            "id",
            "uuid",
            "code",
            "name",
            "area",
            "description",
            "is_active",
            "township",
            "township_name",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "uuid",
            "created_at",
            "updated_at",
            "township",
        )

    def validate_code(self, value):

        value = value.strip().upper()

        if len(value) < 2:
            raise serializers.ValidationError(
                "کد ویلا حداقل باید دو کاراکتر باشد."
            )

        return value

    def validate_area(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "متراژ باید بزرگتر از صفر باشد."
            )

        return value

    def validate_name(self, value):

        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(
                "نام ویلا معتبر نیست."
            )

        return value

    def validate(self, attrs):

        township = self.context["township"]

        code = attrs["code"].strip().upper()

        queryset = Villa.objects.filter(
            township=township,
            code=code,
        )

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                {
                    "code": "این کد قبلاً در این شهرک ثبت شده است."
                }
            )

        attrs["code"] = code

        return attrs

    def create(self, validated_data):

        township = self.context["township"]

        villa = Villa.objects.create(
            township=township,
            **validated_data,
        )

        return villa
    
# =========================
# Residence Serializer
# =========================

class ResidenceSerializer(serializers.ModelSerializer):

    villa_code = serializers.CharField(
        source="villa.code",
        read_only=True,
    )

    villa_name = serializers.CharField(
        source="villa.name",
        read_only=True,
    )

    resident_type_display = serializers.CharField(
        source="get_resident_type_display",
        read_only=True,
    )

    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    mobile = serializers.CharField(
        source="user.mobile",
        read_only=True,
    )
    def has_date_overlap(
        self,
        queryset,
        start_date,
        end_date,
    ):

        for residence in queryset:

            current_start = residence.start_date

            current_end = residence.end_date or date.max

            new_end = end_date or date.max

            if current_start <= new_end and start_date <= current_end:
                return True

        return False
    
    class Meta:

        model = Residence

        fields = (
            "id",
            "uuid",
            "user",
            "username",
            "mobile",
            "villa",
            "villa_code",
            "villa_name",
            "resident_type",
            "resident_type_display",
            "family_count",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "uuid",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):

        township = self.context["township"]

        user = attrs["user"]
        villa = attrs["villa"]

        resident_type = attrs["resident_type"]

        start_date = attrs["start_date"]
        end_date = attrs.get("end_date")

        # -----------------------------
        # تاریخ پایان
        # -----------------------------

        if end_date:

            if end_date < start_date:

                raise serializers.ValidationError(
                    {
                        "end_date": "تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد."
                    }
                )

        # -----------------------------
        # بررسی شهرک ویلا
        # -----------------------------

        if villa.township != township:

            raise serializers.ValidationError(
                {
                    "villa": "ویلا متعلق به شهرک فعال نیست."
                }
            )

        # -----------------------------
        # بررسی عضویت کاربر
        # -----------------------------

        if not Membership.objects.filter(
            user=user,
            township=township,
            is_active=True,
        ).exists():

            raise serializers.ValidationError(
                {
                    "user": "این کاربر عضو شهرک فعال نیست."
                }
            )

        # -----------------------------
        # فقط یک OWNER فعال
        # -----------------------------

        if resident_type == Residence.ResidentType.OWNER:

            queryset = Residence.objects.filter(
                villa=villa,
                resident_type=Residence.ResidentType.OWNER,
                is_active=True,
                end_date__isnull=True,
            )

            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():

                raise serializers.ValidationError(
                    {
                        "resident_type":
                        "برای این ویلا مالک فعال وجود دارد."
                    }
                )


        # -----------------------------
        # فقط یک TENANT فعال
        # -----------------------------

        if resident_type == Residence.ResidentType.TENANT:

            queryset = Residence.objects.filter(
                villa=villa,
                resident_type=Residence.ResidentType.TENANT,
                is_active=True,
            )

            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if self.has_date_overlap(
                queryset,
                start_date,
                end_date,
            ):

                raise serializers.ValidationError(
                    {
                        "resident_type":
                        "بازه زمانی مستأجر با یک مستأجر دیگر همپوشانی دارد."
                    }
                )

        family_count = attrs.get(
        "family_count",
        1,
    )

        if family_count < 1:

            raise serializers.ValidationError(
                {
                    "family_count":
                    "تعداد افراد ساکن باید حداقل ۱ باشد."
                }
            )

        if family_count > 30:

            raise serializers.ValidationError(
                {
                    "family_count":
                    "تعداد افراد ساکن غیرمعتبر است."
                }
            )
        return attrs