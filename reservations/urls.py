from django.urls import path, include

from rest_framework.routers import DefaultRouter

from .views import (
    ReservationViewSet,
    ReservationSlotViewSet,
    FacilityCalendarAPIView,
)

router = DefaultRouter()

# توجه: باید قبل از ثبت ReservationViewSet با پیشوند خالی ثبت شود
# در غیر این صورت الگوی pk آن با مسیر slots/ تداخل پیدا می‌کند.
router.register(
    r"slots",
    ReservationSlotViewSet,
    basename="reservation-slot",
)

router.register(
    r"",
    ReservationViewSet,
    basename="reservation",
)

urlpatterns = [

    path(

        "calendar/<int:facility_id>/",

        FacilityCalendarAPIView.as_view(),

        name="facility-calendar",

    ),

    path(

        "",

        include(router.urls),

    ),

]
