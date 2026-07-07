import os
from django.db import models
from core.models import BaseModel
from django.db.models.signals import post_save
from django.dispatch import receiver


def township_logo_path(instance, filename):
    ext = filename.split('.')[-1]
    return f"townships/{instance.code}/logo.{ext}"


class Township(BaseModel):

    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    logo = models.ImageField(upload_to=township_logo_path, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "townships"
        ordering = ["name"]

    def __str__(self):
        return self.name


class TownshipSetting(BaseModel):

    township = models.OneToOneField(
        Township,
        on_delete=models.CASCADE,
        related_name="settings"
    )

    primary_color = models.CharField(max_length=7, default="#1976D2")
    secondary_color = models.CharField(max_length=7, default="#FFFFFF")

    reservation_enabled = models.BooleanField(default=True)
    online_payment_enabled = models.BooleanField(default=False)
    guest_access_enabled = models.BooleanField(default=False)

    class Meta:
        db_table = "township_settings"

