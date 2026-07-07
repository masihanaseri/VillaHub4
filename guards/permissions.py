from rest_framework.permissions import BasePermission, SAFE_METHODS


class HasActiveTownship(BasePermission):

    message = "برای مدیریت نگهبان‌ها باید یک شهرک فعال انتخاب کنید."

    def has_permission(self, request, view):

        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.active_township_id,
        )


class IsGuardOfActiveTownship(BasePermission):

    message = "این نگهبان متعلق به شهرک فعال شما نیست."

    def has_object_permission(self, request, view, obj):

        return obj.township_id == request.user.active_township_id


class CanManageGuards(BasePermission):
    """
    خواندن آزاد است، اما نوشتن (ایجاد/ویرایش/حذف/تغییر وضعیت) نیاز به مجوز
    صریح 'guards.manage' دارد (در صورت وجود سیستم نقش/مجوز accounts).
    """

    required_permission = "guards.manage"

    def has_permission(self, request, view):

        if request.method in SAFE_METHODS:

            return True

        if not (request.user and request.user.is_authenticated):

            return False

        if not hasattr(request.user, "has_permission"):

            return True

        return request.user.has_permission(
            self.required_permission,
        )
