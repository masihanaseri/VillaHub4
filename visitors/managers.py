from django.db import models


class VisitorQuerySet(models.QuerySet):

    def active(self):

        return self.filter(

            status="CHECKED_IN",

        )

    def approved(self):

        return self.filter(

            status="APPROVED",

        )

    def today(self):

        from django.utils import timezone

        return self.filter(

            valid_from__date=timezone.localdate(),

        )


class VisitorManager(models.Manager):

    def get_queryset(self):

        return VisitorQuerySet(

            self.model,

            using=self._db,

        )

    def active(self):

        return self.get_queryset().active()

    def approved(self):

        return self.get_queryset().approved()

    def today(self):

        return self.get_queryset().today()