from datetime import datetime

from django.shortcuts import get_object_or_404

from django.utils import timezone


from rest_framework import viewsets

from rest_framework.decorators import action

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from core.api.base import TownshipRequiredAPIView

from facilities.models import Facility
from .availability import AvailabilityService
from .models import Reservation, ReservationSlot

from .serializers import (
    ReservationSerializer,
    ReservationSlotSerializer,
)

from .services import ReservationService

from .calendar_service import ReservationCalendarService


class ReservationViewSet(viewsets.ModelViewSet):

    serializer_class = ReservationSerializer

    permission_classes = [

        IsAuthenticated,

    ]

    def get_queryset(self):

        township = self.request.user.active_township

        if township is None:

            return Reservation.objects.none()

        return (

            Reservation.objects.filter(

                facility__township=township,

            )

            .select_related(

                "facility",

                "slot",

                "residence",

                "residence__villa",

                "residence__user",

                "created_by",

                "approved_by",

                "cancelled_by",

            )

            .prefetch_related(

                "payments",

                "logs",

            )

            .order_by(

                "-start_datetime",

            )

        )

    def get_serializer_context(self):

        context = super().get_serializer_context()

        context["township"] = (

            self.request.user.active_township

        )

        return context

    # ==================================================
    # تایید رزرو
    # ==================================================

    @action(
        detail=True,
        methods=["post"],
    )
    def approve(
        self,
        request,
        pk=None,
    ):

        reservation = self.get_object()

        ReservationService.approve_reservation(

            reservation=reservation,

            approved_by=request.user,

            note=request.data.get(
                "note",
                "",
            ),

        )

        serializer = self.get_serializer(
            reservation,
        )

        return Response(
            serializer.data,
        )

    # ==================================================
    # رد رزرو
    # ==================================================

    @action(
        detail=True,
        methods=["post"],
    )
    def reject(
        self,
        request,
        pk=None,
    ):

        reservation = self.get_object()

        ReservationService.reject_reservation(

            reservation=reservation,

            rejected_by=request.user,

            reason=request.data.get(
                "reason",
                "",
            ),

        )

        serializer = self.get_serializer(
            reservation,
        )

        return Response(
            serializer.data,
        )

    # ==================================================
    # لغو رزرو
    # ==================================================

    @action(
        detail=True,
        methods=["post"],
    )
    def cancel(
        self,
        request,
        pk=None,
    ):

        reservation = self.get_object()

        ReservationService.cancel_reservation(

            reservation=reservation,

            cancelled_by=request.user,

            reason=request.data.get(
                "reason",
                "",
            ),

        )

        serializer = self.get_serializer(
            reservation,
        )

        return Response(
            serializer.data,
        )

    # ==================================================
    # Check In
    # ==================================================

    @action(
        detail=True,
        methods=["post"],
    )
    def checkin(
        self,
        request,
        pk=None,
    ):

        reservation = self.get_object()

        ReservationService.check_in(

            reservation=reservation,

            user=request.user,

        )

        serializer = self.get_serializer(
            reservation,
        )

        return Response(
            serializer.data,
        )

    # ==================================================
    # Check Out
    # ==================================================

    @action(
        detail=True,
        methods=["post"],
    )
    def checkout(
        self,
        request,
        pk=None,
    ):

        reservation = self.get_object()

        ReservationService.check_out(

            reservation=reservation,

            user=request.user,

        )

        serializer = self.get_serializer(
            reservation,
        )

        return Response(
            serializer.data,
        )
    # ==================================================
    # ثبت پرداخت
    # ==================================================

    @action(
        detail=True,
        methods=["post"],
    )
    def payment(
        self,
        request,
        pk=None,
    ):

        reservation = self.get_object()

        ReservationService.register_payment(

            reservation=reservation,

            amount=request.data["amount"],

            payment_method=request.data["payment_method"],

            payment_type=request.data["payment_type"],

            created_by=request.user,

            reference_number=request.data.get(
                "reference_number",
                "",
            ),

            note=request.data.get(
                "note",
                "",
            ),

        )

        serializer = self.get_serializer(
            reservation,
        )

        return Response(
            serializer.data,
        )

    # ==================================================
    # استرداد وجه
    # ==================================================

    @action(
        detail=True,
        methods=["post"],
    )
    def refund(
        self,
        request,
        pk=None,
    ):

        reservation = self.get_object()

        ReservationService.refund(

            reservation=reservation,

            amount=request.data["amount"],

            created_by=request.user,

            payment_method=request.data.get(
                "payment_method",
                "CASH",
            ),

            reference_number=request.data.get(
                "reference_number",
                "",
            ),

            note=request.data.get(
                "note",
                "",
            ),

        )

        serializer = self.get_serializer(
            reservation,
        )

        return Response(
            serializer.data,
        )

    # ==================================================
    # محاسبه مبلغ رزرو
    # ==================================================

    @action(
        detail=False,
        methods=["post"],
    )
    def calculate_price(
        self,
        request,
    ):

        facility = Facility.objects.get(
            pk=request.data["facility"],
        )

        start_datetime = datetime.fromisoformat(
            request.data["start_datetime"]
        )

        end_datetime = datetime.fromisoformat(
            request.data["end_datetime"]
        )

        if timezone.is_naive(start_datetime):

            start_datetime = timezone.make_aware(
                start_datetime
            )

        if timezone.is_naive(end_datetime):

            end_datetime = timezone.make_aware(
                end_datetime
            )

        result = ReservationService.calculate_price(

            facility=facility,

            start_datetime=start_datetime,

            end_datetime=end_datetime,

            guest_count=request.data.get(
                "guest_count",
                1,
            ),

        )            

        return Response(

            {

                "price_snapshot": result[0],

                "deposit_snapshot": result[1],

                "total_price": result[2],

            }

        )
    
    # ==================================================
    # بررسی ظرفیت قبل از رزرو
    # ==================================================

    @action(
        detail=False,
        methods=["post"],
    )
    def availability(
        self,
        request,
    ):

        facility = Facility.objects.get(
            pk=request.data["facility"],
        )

        start_datetime = datetime.fromisoformat(
            request.data["start_datetime"]
        )

        end_datetime = datetime.fromisoformat(
            request.data["end_datetime"]
        )

        if timezone.is_naive(start_datetime):

            start_datetime = timezone.make_aware(
                start_datetime
            )

        if timezone.is_naive(end_datetime):

            end_datetime = timezone.make_aware(
                end_datetime
            )

        capacity = AvailabilityService.remaining_capacity(

            facility=facility,

            start_datetime=start_datetime,

            end_datetime=end_datetime,

        )

        return Response({

            "remaining_capacity": capacity,

            "available": (

                capacity is None

                or

                capacity > 0

            ),

        })

    # ==================================================
    # رزروهای امروز
    # ==================================================

    @action(
        detail=False,
        methods=["get"],
    )
    def today(
        self,
        request,
    ):

        queryset = self.get_queryset().filter(

            start_datetime__date=timezone.localdate(),

        )

        serializer = self.get_serializer(

            queryset,

            many=True,

        )

        return Response(

            serializer.data,

        )

    # ==================================================
    # رزروهای آینده
    # ==================================================

    @action(
        detail=False,
        methods=["get"],
    )
    def upcoming(
        self,
        request,
    ):

        queryset = self.get_queryset().filter(

            start_datetime__gte=timezone.now(),

        )

        serializer = self.get_serializer(

            queryset,

            many=True,

        )

        return Response(

            serializer.data,

        )


# ==================================================
# مدیریت سانس‌های امکانات (Slots)
# ==================================================

class ReservationSlotViewSet(viewsets.ModelViewSet):
    """
    مدیریت سانس‌های قابل رزرو یک امکان (booking_mode=SLOT)
    """

    serializer_class = ReservationSlotSerializer

    permission_classes = [

        IsAuthenticated,

    ]

    def get_queryset(self):

        township = self.request.user.active_township

        if township is None:

            return ReservationSlot.objects.none()

        queryset = (

            ReservationSlot.objects.filter(

                facility__township=township,

            )

            .select_related(
                "facility",
            )

        )

        facility_id = self.request.query_params.get(
            "facility",
        )

        if facility_id:

            queryset = queryset.filter(
                facility_id=facility_id,
            )

        return queryset


# ==================================================
# تقویم رزرو یک امکان
# ==================================================

class FacilityCalendarAPIView(TownshipRequiredAPIView):
    """
    نمایش تقویم روزانه ظرفیت آزاد یک امکان برای رزرو
    """

    def get(self, request, facility_id):

        facility = get_object_or_404(

            Facility,

            pk=facility_id,

            township=request.township,

        )

        start_date_param = request.query_params.get(
            "start_date",
        )

        if start_date_param:

            start_date = datetime.strptime(
                start_date_param,
                "%Y-%m-%d",
            ).date()

        else:

            start_date = timezone.localdate()

        days = int(
            request.query_params.get(
                "days",
                30,
            )
        )

        if facility.booking_mode == Facility.BookingMode.SLOT:

            slots = facility.slots.filter(
                is_active=True,
            )

            data = ReservationSlotSerializer(
                slots,
                many=True,
            ).data

            return Response(
                {
                    "facility": facility.id,
                    "booking_mode": facility.booking_mode,
                    "slots": data,
                }
            )

        result = ReservationCalendarService.daily_slots(

            facility=facility,

            start_date=start_date,

            days=days,

        )

        return Response(
            {
                "facility": facility.id,
                "booking_mode": facility.booking_mode,
                "days": result,
            }
        )
