from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class AppConfigView(APIView):
    """تنظیمات اپلیکیشن برای شهرک فعال کاربر"""
    permission_classes = [IsAuthenticated]

    def get(self, request):

        township = request.user.active_township

        if not township:
            return Response({
                "error": "ابتدا یک شهرک را انتخاب کنید"
            }, status=400)

        # بررسی وجود settings
        if not hasattr(township, "settings"):
            return Response({
                "error": "تنظیمات شهرک یافت نشد"
            }, status=500)

        settings_obj = township.settings

        return Response({
            "township": {
                "id": township.id,
                "code": township.code,
                "name": township.name,
                # اصلاح: استفاده از township.logo به جای settings_obj.township.logo
                "logo": request.build_absolute_uri(township.logo.url) if township.logo else None,
                "primary_color": settings_obj.primary_color,
                "secondary_color": settings_obj.secondary_color,
            },
            "features": {
                "reservation": settings_obj.reservation_enabled,
                "online_payment": settings_obj.online_payment_enabled,
                "guest_access": settings_obj.guest_access_enabled,
            }
        })
