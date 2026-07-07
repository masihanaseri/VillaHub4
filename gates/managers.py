from django.db import models


class GateQuerySet(models.QuerySet):

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

    def with_coordinates(self):

        return self.exclude(
            latitude__isnull=True,
        ).exclude(
            longitude__isnull=True,
        )


class GateManager(models.Manager):

    def get_queryset(self):

        return GateQuerySet(
            self.model,
            using=self._db,
        )

    def active(self):

        return self.get_queryset().active()

    def inactive(self):

        return self.get_queryset().inactive()

    def for_township(self, township):

        return self.get_queryset().for_township(township)

    def with_coordinates(self):

        return self.get_queryset().with_coordinates()
