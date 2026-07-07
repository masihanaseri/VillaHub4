from datetime import datetime, timedelta

from django.utils import timezone

from .availability import AvailabilityService


class ReservationCalendarService:

    @staticmethod
    def hourly_slots(
        *,
        facility,
        date,
    ):

        slots = []

        current = datetime.combine(
            date,
            facility.available_from,
        )

        end = datetime.combine(
            date,
            facility.available_until,
        )

        while current < end:

            next_time = current + timedelta(
                minutes=facility.reservation_interval,
            )

            start = timezone.make_aware(current)

            finish = timezone.make_aware(next_time)

            capacity = (
                AvailabilityService.remaining_capacity(
                    facility=facility,
                    start_datetime=start,
                    end_datetime=finish,
                )
            )

            slots.append({

                "start": start,

                "end": finish,

                "capacity": capacity,

                "available": (
                    capacity is None
                    or
                    capacity > 0
                ),

            })

            current = next_time

        return slots
    
    @staticmethod
    def daily_slots(
        *,
        facility,
        start_date,
        days=30,
    ):

        result = []

        for i in range(days):

            day = start_date + timedelta(days=i)

            result.append({

                "date": day,

                "slots": ReservationCalendarService.hourly_slots(

                    facility=facility,

                    date=day,

                ),

            })

        return result    