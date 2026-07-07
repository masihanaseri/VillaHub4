from django.db import models


class NotificationQuerySet(models.QuerySet):

    def unread(self):

        return self.filter(
            is_read=False,
        )

    def read(self):

        return self.filter(
            is_read=True,
        )

    def pending(self):

        return self.filter(
            status="PENDING",
        )

    def sent(self):

        return self.filter(
            status="SENT",
        )

    def failed(self):

        return self.filter(
            status="FAILED",
        )


class NotificationManager(models.Manager):

    def get_queryset(self):

        return NotificationQuerySet(
            self.model,
            using=self._db,
        )

    def unread(self):

        return self.get_queryset().unread()

    def read(self):

        return self.get_queryset().read()

    def pending(self):

        return self.get_queryset().pending()

    def sent(self):

        return self.get_queryset().sent()

    def failed(self):

        return self.get_queryset().failed()