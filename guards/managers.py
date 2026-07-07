from django.db import models


class GuardQuerySet(models.QuerySet):

    def active(self):

        return self.filter(
            is_active=True,
        )

    def inactive(self):

        return self.filter(
            is_active=False,
        )

    def for_township(self, township):

        if township is None:

            return self.none()

        return self.filter(
            township=township,
        )

    def on_shift(self):

        return self.filter(
            shifts__ended_at__isnull=True,
        ).distinct()


class GuardManager(models.Manager):

    def get_queryset(self):

        return GuardQuerySet(
            self.model,
            using=self._db,
        )

    def active(self):

        return self.get_queryset().active()

    def inactive(self):

        return self.get_queryset().inactive()

    def for_township(self, township):

        return self.get_queryset().for_township(township)

    def on_shift(self):

        return self.get_queryset().on_shift()
