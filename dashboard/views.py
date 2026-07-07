from rest_framework.response import Response
from rest_framework import status
from core.api.base import TownshipRequiredAPIView


class DashboardHomeView(TownshipRequiredAPIView):
    """اطلاعات اصلی داشبورد شهرک"""

    def get(self, request):

        township = request.township

        # settings توسط signal ایجاد می‌شود اما اگر وجود نداشت خطا نمی‌دهیم
        if not hasattr(township, "settings") or township.settings is None:
            return Response({
                "error": "تنظیمات شهرک یافت نشد. با مدیر سیستم تماس بگیرید."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        settings_obj = township.settings

        # جمع‌آوری اطلاعات کاربر
        user_roles = list(
            request.user.get_active_roles().values_list("name", flat=True)
        )

        return Response({
            "township": {
                "id": township.id,
                "code": township.code,
                "name": township.name,
                "logo": request.build_absolute_uri(township.logo.url) if township.logo else None,
                "primary_color": settings_obj.primary_color,
                "secondary_color": settings_obj.secondary_color,
            },
            "features": {
                "reservation_enabled": settings_obj.reservation_enabled,
                "online_payment_enabled": settings_obj.online_payment_enabled,
                "guest_access_enabled": settings_obj.guest_access_enabled,
            },
            "user": {
                "username": request.user.username,
                "email": request.user.email,
                "roles": user_roles,
            }
        })
