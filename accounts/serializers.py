from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Invitation, Membership


# =========================
# Invitation Serializer
# =========================
class InvitationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Invitation
        fields = (
            "mobile",
            "role",
        )

    def validate_mobile(self, value):

        value = value.strip()

        if not value.isdigit():
            raise serializers.ValidationError(
                "شماره موبایل فقط باید شامل عدد باشد."
            )

        if len(value) != 11:
            raise serializers.ValidationError(
                "شماره موبایل باید 11 رقم باشد."
            )

        if not value.startswith("09"):
            raise serializers.ValidationError(
                "شماره موبایل باید با 09 شروع شود."
            )

        return value

    def validate(self, attrs):

        township = self.context.get("township")
        mobile = attrs["mobile"]

        if Invitation.objects.filter(
            township=township,
            mobile=mobile,
            is_used=False
        ).exists():
            raise serializers.ValidationError(
                {
                    "mobile": "برای این شماره موبایل قبلاً دعوت نامه فعال ایجاد شده است."
                }
            )

        return attrs

    def create(self, validated_data):

        township = self.context["township"]

        invitation = Invitation.objects.create(
            township=township,
            mobile=validated_data["mobile"],
            role=validated_data["role"],
        )

        return invitation


# =========================
# Accept Invitation Serializer
# =========================
class AcceptInvitationSerializer(serializers.Serializer):

    mobile = serializers.CharField()
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):

        invitation = self.context["invitation"]
        mobile = attrs["mobile"]

        User = get_user_model()

        # 1. بررسی تطابق موبایل با دعوت‌نامه
        if invitation.mobile != mobile:
            raise serializers.ValidationError(
                {"mobile": "شماره موبایل با دعوت‌نامه مطابقت ندارد."}
            )

        # 2. بررسی username تکراری
        if User.objects.filter(username=attrs["username"]).exists():
            raise serializers.ValidationError(
                {"username": "این نام کاربری قبلاً استفاده شده است."}
            )

        # 3. بررسی موبایل تکراری در سیستم
        if User.objects.filter(mobile=mobile).exists():
            raise serializers.ValidationError(
                {"mobile": "این شماره قبلاً ثبت شده است."}
            )

        return attrs

    def create(self, validated_data):

        invitation = self.context["invitation"]
        User = get_user_model()

        # 1. ساخت کاربر
        user = User.objects.create_user(
            username=validated_data["username"],
            mobile=validated_data["mobile"],
            password=validated_data["password"],
        )

        # 2. ساخت membership
        Membership.objects.create(
            user=user,
            township=invitation.township,
            role=invitation.role,
        )

        # 3. تنظیم شهرک فعال
        user.active_township = invitation.township
        user.save(update_fields=["active_township"])

        # 4. مصرف شدن دعوت‌نامه
        invitation.is_used = True
        invitation.save(update_fields=["is_used"])

        return user