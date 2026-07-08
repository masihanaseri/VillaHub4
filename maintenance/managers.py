from django.db import models


class MaintenanceRequestManager(models.Manager):

    def open(self):
        return self.filter(status=self.model.Status.OPEN)

    def urgent(self):
        return self.filter(priority=self.model.Priority.URGENT)

    def active(self):
        return self.exclude(
            status__in=[
                self.model.Status.CLOSED,
                self.model.Status.CANCELLED,
            ]
        )