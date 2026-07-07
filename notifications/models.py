from django.conf import settings
from django.db import models
from .managers import NotificationManager
from core.models import BaseModel


class Notification(BaseModel):

    class NotificationType(models.TextChoices):

        RESERVATION = "RESERVATION", "رزرو"

        PAYMENT = "PAYMENT", "پرداخت"

        CHARGE = "CHARGE", "شارژ"

        COMPLAINT = "COMPLAINT", "شکایت"

        VISITOR = "VISITOR", "مهمان"

        ANNOUNCEMENT = "ANNOUNCEMENT", "اطلاعیه"

        SYSTEM = "SYSTEM", "سیستم"

    class Priority(models.TextChoices):

        LOW = "LOW", "کم"

        NORMAL = "NORMAL", "عادی"

        HIGH = "HIGH", "زیاد"

        URGENT = "URGENT", "فوری"

    class Status(models.TextChoices):

        PENDING = "PENDING", "در انتظار"

        SENT = "SENT", "ارسال شده"

        FAILED = "FAILED", "ناموفق"

        CANCELLED = "CANCELLED", "لغو شده"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    title = models.CharField(
        max_length=200,
    )

    message = models.TextField()

    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    is_read = models.BooleanField(
        default=False,
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    objects = NotificationManager()

    class Meta:

        db_table = "notifications"

        ordering = [
            "-created_at",
        ]

        verbose_name = "اعلان"

        verbose_name_plural = "اعلان‌ها"

    def __str__(self):

        return f"{self.title}"
    
class NotificationLog(BaseModel):

    class Channel(models.TextChoices):

        IN_APP = "IN_APP", "داخل برنامه"

        SMS = "SMS", "پیامک"

        EMAIL = "EMAIL", "ایمیل"

        PUSH = "PUSH", "Push"

    class Status(models.TextChoices):

        PENDING = "PENDING", "در انتظار"

        SENDING = "SENDING", "در حال ارسال"

        SENT = "SENT", "ارسال شده"

        FAILED = "FAILED", "ناموفق"

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="logs",
    )

    channel = models.CharField(
        max_length=20,
        choices=Channel.choices,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    receiver = models.CharField(
        max_length=255,
    )

    provider = models.CharField(
        max_length=100,
        blank=True,
    )

    provider_message_id = models.CharField(
        max_length=255,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:

        db_table = "notification_logs"

        ordering = [
            "-created_at",
        ]

        verbose_name = "گزارش اعلان"

        verbose_name_plural = "گزارش اعلان‌ها"

    def __str__(self):

        return (
            f"{self.notification.title}"
            f" | "
            f"{self.channel}"
        )
