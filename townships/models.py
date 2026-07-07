import os
from django.db import models
from core.models import BaseModel
from django.db.models.signals import post_save
from django.dispatch import receiver
from config import settings


def township_logo_path(instance, filename):
    ext = filename.split('.')[-1]
    return f"townships/{instance.code}/logo.{ext}"


class Township(BaseModel):

    code = models.CharField(max_length=20, unique=True, db_index=True)
    
    name = models.CharField(max_length=150)
    
    logo = models.ImageField(upload_to=township_logo_path, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    phone = models.CharField(
        max_length=20,
        blank=True,
    )

    mobile = models.CharField(
        max_length=20,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    website = models.URLField(
        blank=True,
    )

    province = models.CharField(
        max_length=100,
        blank=True,
    )

    city = models.CharField(
        max_length=100,
        blank=True,
    )

    address = models.TextField(
        blank=True,
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="managed_townships",
    )

    manager = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name="managed_townships",
)

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
    
    chat_enabled = models.BooleanField(
        default=True,
    )

    private_chat_enabled = models.BooleanField(
        default=True,
    )

    marketplace_enabled = models.BooleanField(
        default=True,
    )

    polls_enabled = models.BooleanField(
        default=True,
    )

    announcements_enabled = models.BooleanField(
        default=True,
    )

    ai_assistant_enabled = models.BooleanField(
        default=True,
    )

    max_storage_gb = models.PositiveIntegerField(
        default=10,
    )

    max_users = models.PositiveIntegerField(
        default=500,
    )

    class Meta:
        db_table = "township_settings"

