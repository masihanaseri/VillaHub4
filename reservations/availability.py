from django.db.models import Sum

from reservations.models import Reservation
from facilities.models import Facility


class AvailabilityService:

    @staticmethod
    def available_capacity(
        *,
        facility,
        start_datetime,
        end_datetime,
    ):

        reservations = Reservation.objects.filter(

            facility=facility,

            reservation_status__in=[

                Reservation.ReservationStatus.REQUESTED,

                Reservation.ReservationStatus.APPROVED,

            ],

            start_datetime__lt=end_datetime,

            end_datetime__gt=start_datetime,

        )

        # -------------------------
        # رزرو انحصاری
        # -------------------------

        if (
            facility.reservation_policy
            ==
            Facility.ReservationPolicy.EXCLUSIVE
        ):

            if reservations.exists():

                return 0

            return 1

        # -------------------------
        # هر ویلا
        # -------------------------

        if (
            facility.reservation_policy
            ==
            Facility.ReservationPolicy.PER_VILLA
        ):

            return None

        # -------------------------
        # ظرفیت
        # -------------------------

        reserved = (

            reservations.aggregate(

                total=Sum("guest_count")

            )["total"]

            or

            0

        )

        return max(

            facility.capacity - reserved,

            0,

        )

    @staticmethod
    def is_available(
        *,
        facility,
        start_datetime,
        end_datetime,
        guest_count,
    ):

        capacity = AvailabilityService.available_capacity(

            facility=facility,

            start_datetime=start_datetime,

            end_datetime=end_datetime,

        )

        if capacity is None:

            return True

        return capacity >= guest_count
    
    @staticmethod
    def remaining_capacity(
        *,
        facility,
        start_datetime,
        end_datetime,
    ):

        return AvailabilityService.available_capacity(

            facility=facility,

            start_datetime=start_datetime,

            end_datetime=end_datetime,

        )    