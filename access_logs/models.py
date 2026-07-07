from django.db import models

from django.utils import timezone

from core.models import BaseModel

from .managers import AccessLogManager

from .validators import validate_plate_number


class AccessLog(BaseModel):
    """
    دفترچه واقعی تردد از درب‌ها.
    زنجیره کامل معماری اینجا به هم می‌رسد:

        Visitor  ─┐
                   ├─>  Gate  ─>  Guard  ─>  AccessLog
        Residence ─┘

    این مدل یک لاگ ممیزی (Audit Log) است: پس از ثبت، ویرایش یا حذف نمی‌شود
    (نگاه کنید به AccessLogService و AccessLogViewSet).
    """

    class Direction(models.TextChoices):

        IN = "IN", "ورود"

        OUT = "OUT", "خروج"

    class AccessMethod(models.TextChoices):

        MANUAL = "MANUAL", "ثبت دستی توسط نگهبان"

        QR = "QR", "کد QR"

        PLATE = "PLATE", "تشخیص پلاک"

        CARD = "CARD", "کارت تردد"

    township = models.ForeignKey(
        "townships.Township",
        on_delete=models.CASCADE,
        related_name="access_logs",
        verbose_name="شهرک",
    )

    gate = models.ForeignKey(
        "gates.Gate",
        on_delete=models.PROTECT,
        related_name="access_logs",
        verbose_name="درب",
    )

    guard = models.ForeignKey(
        "guards.Guard",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="access_logs",
        verbose_name="نگهبان ثبت‌کننده",
    )

    visitor = models.ForeignKey(
        "visitors.Visitor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="access_logs",
        verbose_name="مهمان",
    )

    residence = models.ForeignKey(
        "villas.Residence",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="access_logs",
        verbose_name="سکونت (ساکن)",
    )

    direction = models.CharField(
        max_length=10,
        choices=Direction.choices,
        verbose_name="جهت تردد",
    )

    access_method = models.CharField(
        max_length=20,
        choices=AccessMethod.choices,
        default=AccessMethod.MANUAL,
        verbose_name="روش ثبت",
    )

    plate_number = models.CharField(
        max_length=30,
        blank=True,
        validators=[validate_plate_number],
        verbose_name="پلاک خودرو",
    )

    occurred_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="زمان تردد",
    )

    notes = models.TextField(
        blank=True,
        verbose_name="توضیحات",
    )

    objects = AccessLogManager()

    class Meta:

        db_table = "access_logs"

        ordering = [
            "-occurred_at",
        ]

        verbose_name = "رویداد تردد"

        verbose_name_plural = "رویدادهای تردد"

        constraints = [

            models.CheckConstraint(
                condition=~(
                    models.Q(visitor__isnull=False)
                    & models.Q(residence__isnull=False)
                ),
                name="access_log_visitor_xor_residence",
            ),

        ]

        indexes = [

            models.Index(
                fields=["township", "occurred_at"],
                name="idx_accesslog_township_time",
            ),

            models.Index(
                fields=["gate", "occurred_at"],
                name="idx_accesslog_gate_time",
            ),

            models.Index(
                fields=["visitor"],
                name="idx_accesslog_visitor",
            ),

            models.Index(
                fields=["residence"],
                name="idx_accesslog_residence",
            ),

        ]

    def __str__(self):

        subject = self.subject_display

        return (
            f"{self.gate.name} | "
            f"{self.get_direction_display()} | "
            f"{subject} | "
            f"{self.occurred_at:%Y-%m-%d %H:%M}"
        )

    @property
    def subject_display(self):

        if self.visitor_id:

            return f"مهمان: {self.visitor.full_name}"

        if self.residence_id:

            return f"ساکن: {self.residence.user.get_full_name() or self.residence.user.username}"

        if self.plate_number:

            return f"خودرو: {self.plate_number}"

        return "نامشخص"
