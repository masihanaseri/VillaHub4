from django.conf import settings
from django.db import models
from .managers import SmsMessageManager
from core.models import BaseModel

class SmsTemplate(BaseModel):

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    text = models.TextField()

    is_active = models.BooleanField(
        default=True,
    )

    description = models.TextField(
        blank=True,
    )
    objects = SmsMessageManager()
    
    class Meta:
        db_table = "sms_templates"
        ordering = ["name"]

    def __str__(self):
        return self.name

class SmsMessage(BaseModel):

    class Status(models.TextChoices):

        PENDING = "PENDING", "در انتظار"

        SENT = "SENT", "ارسال شد"

        FAILED = "FAILED", "ناموفق"

        DELIVERED = "DELIVERED", "تحویل شد"

    template = models.ForeignKey(
        SmsTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sms_messages",
    )

    mobile = models.CharField(
        max_length=20,
    )

    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    provider = models.CharField(
        max_length=50,
        blank=True,
    )

    provider_message_id = models.CharField(
        max_length=100,
        blank=True,
    )

    error = models.TextField(
        blank=True,
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    

    class Meta:
        db_table = "sms_messages"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.mobile} - {self.status}"
    
class SmsOTP(BaseModel):

    mobile = models.CharField(
        max_length=20,
    )

    code = models.CharField(
        max_length=6,
    )

    is_used = models.BooleanField(
        default=False,
    )

    expires_at = models.DateTimeField()

    class Meta:
        db_table = "sms_otps"
        ordering = ["-created_at"]

    def __str__(self):
        return self.mobile
