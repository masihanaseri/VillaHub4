from rest_framework.permissions import BasePermission, SAFE_METHODS


class HasActiveTownship(BasePermission):
    """
    کاربر باید علاوه بر لاگین بودن، یک شهرک فعال هم انتخاب کرده باشد.
    """

    message = "برای مدیریت درب‌ها باید یک شهرک فعال انتخاب کنید."

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


class IsGateOfActiveTownship(BasePermission):
    """
    محافظت سطح آبجکت: حتی اگر queryset به هر دلیلی صحیح فیلتر نشده باشد،
    کاربر هرگز نباید بتواند دربی خارج از شهرک فعال خودش را تغییر دهد.
    """

    message = "این درب متعلق به شهرک فعال شما نیست."

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):

        return obj.township_id == request.user.active_township_id


class CanManageGates(BasePermission):
    """
    در صورت وجود سیستم نقش/مجوز (accounts.Permission)، مدیریت درب‌ها را
    به کاربرانی که مجوز 'gates.manage' دارند محدود می‌کند.
    خواندن (GET/HEAD/OPTIONS) برای هر کاربر عضو شهرک آزاد است، اما
    نوشتن (POST/PUT/PATCH/DELETE) نیاز به مجوز صریح دارد.
    """

    required_permission = "gates.manage"

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
