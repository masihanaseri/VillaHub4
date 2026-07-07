import uuid

from django.conf import settings

from django.db import models

from django.utils import timezone

from core.models import BaseModel

from .managers import (
    AccessPassManager,
    AccessLogManager,
)

from .validators import (
    validate_latitude,
    validate_longitude,
    validate_device_label,
)


class AccessPass(BaseModel):
    """
    مجوز تردد صادرشده برای یک مهمان (Visitor).

    این مدل قلب زنجیره کنترل تردد است:

        Visitor -> AccessPass -> Gate -> Guard -> AccessLog

    هر ورود/خروج فیزیکی به شهرک باید از طریق یک AccessPass معتبر و
    از طریق AccessControlService انجام و در AccessLog ثبت شود.
    """

    class Status(models.TextChoices):

        PENDING = "PENDING", "در انتظار تایید"

        APPROVED = "APPROVED", "تایید شده"

        REJECTED = "REJECTED", "رد شده"

        CANCELLED = "CANCELLED", "لغو شده"

        CHECKED_IN = "CHECKED_IN", "ورود ثبت‌شده"

        CHECKED_OUT = "CHECKED_OUT", "خروج ثبت‌شده"

        EXPIRED = "EXPIRED", "منقضی"

    township = models.ForeignKey(
        "townships.Township",
        on_delete=models.CASCADE,
        related_name="access_passes",
        verbose_name="شهرک",
    )

    visitor = models.ForeignKey(
        "visitors.Visitor",
        on_delete=models.PROTECT,
        related_name="access_passes",
        verbose_name="مهمان",
    )

    gate = models.ForeignKey(
        "gates.Gate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="access_passes",
        verbose_name="درب مجاز",
        help_text="در صورت خالی بودن، کارت از هر دربی قابل استفاده است.",
    )

    qr_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="کد QR",
    )

    valid_from = models.DateTimeField(
        verbose_name="اعتبار از",
    )

    valid_until = models.DateTimeField(
        verbose_name="اعتبار تا",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="وضعیت",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_access_passes",
        verbose_name="ایجادکننده",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_access_passes",
        verbose_name="تاییدکننده",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان تایید",
    )

    checked_in_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان ورود",
    )

    checked_out_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان خروج",
    )

    notes = models.TextField(
        blank=True,
        verbose_name="توضیحات",
    )

    objects = AccessPassManager()

    class Meta:

        db_table = "access_passes"

        ordering = [
            "-created_at",
        ]

        verbose_name = "کارت تردد"

        verbose_name_plural = "کارت‌های تردد"

        constraints = [

            models.CheckConstraint(
                condition=models.Q(valid_until__gt=models.F("valid_from")),
                name="access_pass_valid_until_after_valid_from",
            ),

        ]

        indexes = [

            models.Index(
                fields=["township", "status"],
                name="idx_apass_township_status",
            ),

            models.Index(
                fields=["gate", "status"],
                name="idx_apass_gate_status",
            ),

            models.Index(
                fields=["visitor"],
                name="idx_apass_visitor",
            ),

            models.Index(
                fields=["valid_from", "valid_until"],
                name="idx_apass_valid_period",
            ),

        ]

    def __str__(self):

        return (
            f"{self.visitor.full_name} | "
            f"{self.get_status_display()}"
        )

    def delete(self, *args, **kwargs):

        raise ValueError(
            "حذف کارت تردد مجاز نیست؛ در صورت نیاز آن را لغو کنید.",
        )

    @property
    def is_expired(self):

        return timezone.now() > self.valid_until

    @property
    def is_valid(self):
        """
        آیا این کارت در همین لحظه برای عبور از درب معتبر است؟
        (تایید شده و در بازه زمانی مجاز)
        """

        return (
            self.status == self.Status.APPROVED
            and self.valid_from <= timezone.now() <= self.valid_until
        )

    @property
    def is_active(self):
        """
        آیا دارنده این کارت هم‌اکنون داخل شهرک است؟ (ورود ثبت شده اما
        هنوز خروج ثبت نشده است)
        """

        return self.status == self.Status.CHECKED_IN


class AccessLog(BaseModel):
    """
    دفترچه ممیزی (Audit Log) هر رویداد واقعی مرتبط با یک AccessPass:
    ورود، خروج، اسکن QR و تلاش‌های ناموفق/رد شده.

        AccessPass -> Gate -> Guard -> AccessLog

    این مدل پس از ثبت تغییرناپذیر است (نگاه کنید به AccessControlService
    و AccessLogViewSet) تا صحت تاریخچه تردد تضمین بماند.
    """

    class Action(models.TextChoices):

        CHECK_IN = "CHECK_IN", "ورود"

        CHECK_OUT = "CHECK_OUT", "خروج"

        DENIED = "DENIED", "رد شده"

        QR_SCAN = "QR_SCAN", "اسکن QR"

        MANUAL = "MANUAL", "ثبت دستی"

        MANAGER = "MANAGER", "اقدام مدیر"

    township = models.ForeignKey(
        "townships.Township",
        on_delete=models.CASCADE,
        related_name="access_control_logs",
        verbose_name="شهرک",
    )

    access_pass = models.ForeignKey(
        AccessPass,
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name="کارت تردد",
    )

    gate = models.ForeignKey(
        "gates.Gate",
        on_delete=models.PROTECT,
        related_name="access_control_logs",
        verbose_name="درب",
    )

    guard = models.ForeignKey(
        "guards.Guard",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="access_control_logs",
        verbose_name="نگهبان ثبت‌کننده",
    )

    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        verbose_name="عملیات",
    )

    device = models.CharField(
        max_length=100,
        blank=True,
        validators=[validate_device_label],
        verbose_name="دستگاه",
        help_text="شناسه دستگاه/اپلیکیشن ثبت‌کننده (مثال: QR-SCANNER-01)",
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[validate_latitude],
        verbose_name="عرض جغرافیایی",
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[validate_longitude],
        verbose_name="طول جغرافیایی",
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="آدرس IP",
    )

    notes = models.TextField(
        blank=True,
        verbose_name="توضیحات",
    )

    objects = AccessLogManager()

    class Meta:

        db_table = "access_control_logs"

        ordering = [
            "-created_at",
        ]

        verbose_name = "رویداد کنترل تردد"

        verbose_name_plural = "رویدادهای کنترل تردد"

        constraints = [

            models.CheckConstraint(
                condition=(
                    models.Q(latitude__isnull=True, longitude__isnull=True)
                    | models.Q(latitude__isnull=False, longitude__isnull=False)
                ),
                name="access_log_lat_lng_both_or_none",
            ),

        ]

        indexes = [

            models.Index(
                fields=["township", "created_at"],
                name="idx_aclog_township_time",
            ),

            models.Index(
                fields=["gate", "created_at"],
                name="idx_aclog_gate_time",
            ),

            models.Index(
                fields=["access_pass", "created_at"],
                name="idx_aclog_pass_time",
            ),

            models.Index(
                fields=["action"],
                name="idx_aclog_action",
            ),

        ]

    def __str__(self):

        return (
            f"{self.access_pass.visitor.full_name} | "
            f"{self.get_action_display()} | "
            f"{self.created_at:%Y-%m-%d %H:%M}"
        )

    def delete(self, *args, **kwargs):

        raise ValueError(
            "حذف رویدادهای کنترل تردد مجاز نیست.",
        )
