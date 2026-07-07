from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotAuthenticated
from rest_framework import status


class TownshipRequiredAPIView(APIView):
    """
    Base view که نیاز به احراز هویت و انتخاب شهرک دارد
    تمام view‌هایی که به شهرک وابسته‌اند باید از این ارث‌بری کنند
    """

    def dispatch(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            raise NotAuthenticated("ابتدا وارد شوید")

        if not request.user.active_township:
            raise PermissionDenied("هیچ شهرکی انتخاب نشده است")

        request.township = request.user.active_township

        return super().dispatch(request, *args, **kwargs)
