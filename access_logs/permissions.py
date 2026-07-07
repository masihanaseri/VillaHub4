from rest_framework.permissions import BasePermission


class HasActiveTownship(BasePermission):

    message = "برای ثبت یا مشاهده تردد باید یک شهرک فعال انتخاب کنید."

    def has_permission(self, request, view):

        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.active_township_id,
        )


class IsAccessLogOfActiveTownship(BasePermission):

    message = "این رویداد تردد متعلق به شهرک فعال شما نیست."

    def has_object_permission(self, request, view, obj):

        return obj.township_id == request.user.active_township_id


class ReadOnlyOrCreateOnly(BasePermission):
    """
    AccessLog یک دفترچه ممیزی است: فقط خواندن (GET) و ثبت رویداد جدید
    (POST) مجاز است. ویرایش/حذف (PUT/PATCH/DELETE) همیشه رد می‌شود، حتی
    برای مدیران، تا صحت تاریخچه تردد تضمین بماند.
    """

    message = "رویدادهای تردد پس از ثبت قابل ویرایش یا حذف نیستند."

    def has_permission(self, request, view):

        return request.method in (
            "GET",
            "HEAD",
            "OPTIONS",
            "POST",
        )
