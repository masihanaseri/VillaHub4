from django.utils.deprecation import MiddlewareMixin


class TownshipMiddleware(MiddlewareMixin):
    """
    تنظیم request.township برای هر درخواست
    اگر کاربر وارد نشده باشد یا شهرک فعال نداشته باشد، مقدار None قرار می‌گیرد
    """

    def process_request(self, request):

        if not hasattr(request, "user") or not request.user.is_authenticated:
            request.township = None
            return

        request.township = request.user.active_township
