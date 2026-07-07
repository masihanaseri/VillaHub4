from django.db import models


class SmsMessageQuerySet(models.QuerySet):

    def pending(self):
        return self.filter(status="PENDING")

    def sent(self):
        return self.filter(status="SENT")

    def failed(self):
        return self.filter(status="FAILED")

    def delivered(self):
        return self.filter(status="DELIVERED")


class SmsMessageManager(models.Manager):

    def get_queryset(self):
        return SmsMessageQuerySet(
            self.model,
            using=self._db,
        )

    def pending(self):
        return self.get_queryset().pending()

    def sent(self):
        return self.get_queryset().sent()

    def failed(self):
        return self.get_queryset().failed()

    def delivered(self):
        return self.get_queryset().delivered()