from django.db import models

from django.utils import timezone


class AccessPassQuerySet(models.QuerySet):
    """
    QuerySet سازمانی برای AccessPass.
    """

    def for_township(self, township):

        if township is None:

            return self.none()

        return self.filter(
            township=township,
        )

    def for_visitor(self, visitor):

        return self.filter(
            visitor=visitor,
        )

    def for_gate(self, gate):

        return self.filter(
            gate=gate,
        )

    def active(self):
        """
        کارت‌هایی که هنوز در چرخه فعال هستند (رد/لغو/منقضی نشده‌اند).
        """

        return self.filter(
            status__in=[
                "PENDING",
                "APPROVED",
                "CHECKED_IN",
            ],
        )

    def approved(self):

        return self.filter(
            status="APPROVED",
        )

    def inside(self):
        """
        کارت‌هایی که دارنده آن‌ها هم‌اکنون داخل شهرک است.
        """

        return self.filter(
            status="CHECKED_IN",
        )

    def expired(self):
        """
        کارت‌هایی که یا صراحتاً منقضی شده‌اند یا بازه اعتبارشان گذشته است.
        """

        return self.filter(
            models.Q(status="EXPIRED")
            | models.Q(valid_until__lt=timezone.now()),
        )

    def today(self):

        return self.filter(
            valid_from__date=timezone.localdate(),
        )


class AccessPassManager(models.Manager):

    def get_queryset(self):

        return AccessPassQuerySet(
            self.model,
            using=self._db,
        )

    def for_township(self, township):

        return self.get_queryset().for_township(township)

    def for_visitor(self, visitor):

        return self.get_queryset().for_visitor(visitor)

    def for_gate(self, gate):

        return self.get_queryset().for_gate(gate)

    def active(self):

        return self.get_queryset().active()

    def approved(self):

        return self.get_queryset().approved()

    def inside(self):

        return self.get_queryset().inside()

    def expired(self):

        return self.get_queryset().expired()

    def today(self):

        return self.get_queryset().today()


class AccessLogQuerySet(models.QuerySet):
    """
    QuerySet سازمانی برای AccessLog.
    """

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

    def for_access_pass(self, access_pass):

        return self.filter(
            access_pass=access_pass,
        )

    def check_ins(self):

        return self.filter(
            action="CHECK_IN",
        )

    def check_outs(self):

        return self.filter(
            action="CHECK_OUT",
        )

    def denied(self):

        return self.filter(
            action="DENIED",
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
            created_at__gte=start_of_day,
        )


class AccessLogManager(models.Manager):

    def get_queryset(self):

        return AccessLogQuerySet(
            self.model,
            using=self._db,
        )

    def for_township(self, township):

        return self.get_queryset().for_township(township)

    def for_gate(self, gate):

        return self.get_queryset().for_gate(gate)

    def for_guard(self, guard):

        return self.get_queryset().for_guard(guard)

    def for_access_pass(self, access_pass):

        return self.get_queryset().for_access_pass(access_pass)

    def check_ins(self):

        return self.get_queryset().check_ins()

    def check_outs(self):

        return self.get_queryset().check_outs()

    def denied(self):

        return self.get_queryset().denied()

    def today(self):

        return self.get_queryset().today()
