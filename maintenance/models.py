from django.conf import settings
from django.db import models

from core.models import BaseModel
from maintenance.managers import MaintenanceRequestManager
from townships.models import Township
from villas.models import Villa


class MaintenanceRequest(BaseModel):

    class Category(models.TextChoices):
        ELECTRICAL = "ELECTRICAL", "برق"
        WATER = "WATER", "آب"
        GAS = "GAS", "گاز"
        GARDEN = "GARDEN", "فضای سبز"
        POOL = "POOL", "استخر"
        BUILDING = "BUILDING", "ساختمان"
        CLEANING = "CLEANING", "نظافت"
        SECURITY = "SECURITY", "امنیتی"
        INTERNET = "INTERNET", "اینترنت"
        OTHER = "OTHER", "سایر"

    class Priority(models.TextChoices):
        LOW = "LOW", "کم"
        NORMAL = "NORMAL", "عادی"
        HIGH = "HIGH", "زیاد"
        URGENT = "URGENT", "فوری"

    class Status(models.TextChoices):
        OPEN = "OPEN", "ثبت شده"
        REVIEW = "REVIEW", "در حال بررسی"
        ASSIGNED = "ASSIGNED", "ارجاع شده"
        IN_PROGRESS = "IN_PROGRESS", "در حال انجام"
        WAITING_PARTS = "WAITING_PARTS", "در انتظار قطعه"
        DONE = "DONE", "انجام شد"
        CLOSED = "CLOSED", "بسته شد"
        REJECTED = "REJECTED", "رد شد"
        CANCELLED = "CANCELLED", "لغو شد"

    township = models.ForeignKey(
        Township,
        on_delete=models.CASCADE,
        related_name="maintenance_requests",
    )

    villa = models.ForeignKey(
        Villa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_requests",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_maintenance_requests",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_maintenance_requests",
    )

    title = models.CharField(max_length=200)

    description = models.TextField()

    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.OTHER,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.OPEN,
    )

    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    final_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    objects = MaintenanceRequestManager()

    class Meta:
        db_table = "maintenance_requests"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class MaintenanceAttachment(BaseModel):

    maintenance = models.ForeignKey(
        MaintenanceRequest,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file = models.FileField(
        upload_to="maintenance/",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = "maintenance_attachments"


class MaintenanceComment(BaseModel):

    maintenance = models.ForeignKey(
        MaintenanceRequest,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    message = models.TextField()

    class Meta:
        db_table = "maintenance_comments"
        ordering = ["created_at"]


class MaintenanceHistory(BaseModel):

    maintenance = models.ForeignKey(
        MaintenanceRequest,
        on_delete=models.CASCADE,
        related_name="history",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    old_status = models.CharField(
        max_length=30,
    )

    new_status = models.CharField(
        max_length=30,
    )

    note = models.TextField(
        blank=True,
    )

    class Meta:
        db_table = "maintenance_history"
        ordering = ["-created_at"]