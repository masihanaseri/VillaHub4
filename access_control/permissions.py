from rest_framework.permissions import (
    BasePermission,
    SAFE_METHODS,
)


class HasActiveTownship(BasePermission):
    """
    کاربر باید علاوه بر لاگین بودن، یک شهرک فعال هم انتخاب کرده باشد.
    """

    message = "برای مدیریت کنترل تردد باید یک شهرک فعال انتخاب کنید."

    def has_permission(
        self,
        request,
        view,
    ):

        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.active_township_id,
        )


class IsAccessPassOfActiveTownship(BasePermission):
    """
    محافظت سطح آبجکت: کاربر هرگز نباید بتواند کارت تردد خارج از شهرک
    فعال خودش را مشاهده یا تغییر دهد.
    """

    message = "این کارت تردد متعلق به شهرک فعال شما نیست."

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):

        return obj.township_id == request.user.active_township_id


class IsAccessLogOfActiveTownship(BasePermission):

    message = "این رویداد کنترل تردد متعلق به شهرک فعال شما نیست."

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):

        return obj.township_id == request.user.active_township_id


class CanManageAccessControl(BasePermission):
    """
    در صورت وجود سیستم نقش/مجوز (accounts.Permission)، عملیات نوشتاری
    (تایید، رد، لغو، ورود، خروج) را به کاربرانی که مجوز
    'access_control.manage' دارند محدود می‌کند. خواندن برای هر عضو
    شهرک آزاد است.
    """

    required_permission = "access_control.manage"

    def has_permission(
        self,
        request,
        view,
    ):

        if request.method in SAFE_METHODS:

            return True

        if not (request.user and request.user.is_authenticated):

            return False

        if not hasattr(request.user, "has_permission"):

            return True

        return request.user.has_permission(
            self.required_permission,
        )


class IsGuardOrManager(BasePermission):
    """
    برخی اکشن‌ها (validate_qr، checkin، checkout) باید فقط توسط نگهبان‌های
    شیفت یا مدیران شهرک قابل استفاده باشند. در صورت نبود پروفایل نگهبان
    برای کاربر جاری، دسترسی به مدیران شهرک (has_permission) واگذار می‌شود.
    """

    message = "فقط نگهبانان یا مدیران شهرک به این عملیات دسترسی دارند."

    def has_permission(
        self,
        request,
        view,
    ):

        if not (request.user and request.user.is_authenticated):

            return False

        if hasattr(request.user, "guard_profile"):

            return True

        if not hasattr(request.user, "has_permission"):

            return True

        return request.user.has_permission(
            "access_control.manage",
        )
