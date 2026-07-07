from django.db import models


class SafeTownshipQuerySet(models.QuerySet):

    def for_township(self, township):
        """
        فقط داده‌های یک township خاص را برمی‌گرداند
        """
        if township is None:
            return self.none()
        return self.filter(township=township)

    def active(self):
        """رکوردهای فعال (اگر مدل is_active داشته باشد)"""
        return self.filter(is_active=True)


class SafeTownshipManager(models.Manager):

    def get_queryset(self):
        return SafeTownshipQuerySet(self.model, using=self._db)

    def for_township(self, township):
        return self.get_queryset().for_township(township)
