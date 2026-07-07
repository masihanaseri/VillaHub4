from django.db import models

from django.utils import timezone


class ReservationManager(models.Manager):

    def active(self):

        return self.filter(

            reservation_status__in=[

                "REQUESTED",

                "APPROVED",

            ]

        )

    def approved(self):

        return self.filter(

            reservation_status="APPROVED",

        )

    def completed(self):

        return self.filter(

            reservation_status="COMPLETED",

        )

    def cancelled(self):

        return self.filter(

            reservation_status="CANCELLED",

        )

    def today(self):

        return self.filter(

            start_datetime__date=timezone.localdate(),

        )

    def upcoming(self):

        return self.filter(

            start_datetime__gte=timezone.now(),

        )

    def unpaid(self):

        return self.filter(

            payment_status="UNPAID",

        )