from django.db import models

from django.utils import timezone


class AccessLogQuerySet(models.QuerySet):

    def entries(self):

        return self.filter(
            direction="IN",
        )

    def exits(self):

        return self.filter(
            direction="OUT",
        )

    def for_township(self, township):

        if township is None:

            return self.none()

        return self.filter(
            township=township,
        )

    def for_gate(self, gate):

        return self.filter(
            gate=gate,
        )

    def for_guard(self, guard):

        return self.filter(
            guard=guard,
        )

    def for_visitor(self, visitor):

        return self.filter(
            visitor=visitor,
        )

    def for_residence(self, residence):

        return self.filter(
            residence=residence,
        )

    def today(self):

        now = timezone.localtime()

        start_of_day = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        return self.filter(
            occurred_at__gte=start_of_day,
        )


class AccessLogManager(models.Manager):

    def get_queryset(self):

        return AccessLogQuerySet(
            self.model,
            using=self._db,
        )

    def entries(self):

        return self.get_queryset().entries()

    def exits(self):

        return self.get_queryset().exits()

    def for_township(self, township):

        return self.get_queryset().for_township(township)

    def for_gate(self, gate):

        return self.get_queryset().for_gate(gate)

    def for_guard(self, guard):

        return self.get_queryset().for_guard(guard)

    def for_visitor(self, visitor):

        return self.get_queryset().for_visitor(visitor)

    def for_residence(self, residence):

        return self.get_queryset().for_residence(residence)

    def today(self):

        return self.get_queryset().today()
