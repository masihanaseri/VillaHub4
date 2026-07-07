from django.conf import settings

from django.db import models

from core.models import BaseModel

from .managers import GuardManager

from .validators import (
    validate_employee_code,
    validate_guard_phone,
)


class Guard(BaseModel):

    class Shift(models.TextChoices):

        MORNING = "MORNING", "صبح"

        EVENING = "EVENING", "عصر"

        NIGHT = "NIGHT", "شب"

    township = models.ForeignKey(
        "townships.Township",
        on_delete=models.CASCADE,
        related_name="guards",
        verbose_name="شهرک",
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="guard_profile",
        verbose_name="کاربر",
    )

    gates = models.ManyToManyField(
        "gates.Gate",
        related_name="guards",
        blank=True,
        verbose_name="درب‌های تحت مسئولیت",
    )

    employee_code = models.CharField(
        max_length=30,
        unique=True,
        validators=[validate_employee_code],
        verbose_name="کد پرسنلی",
    )

    phone = models.CharField(
        max_length=20,
        validators=[validate_guard_phone],
        verbose_name="تلفن",
    )

    shift = models.CharField(
        max_length=20,
        choices=Shift.choices,
        verbose_name="شیفت",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال",
    )

    hired_at = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاریخ استخدام",
    )

    notes = models.TextField(
        blank=True,
        verbose_name="توضیحات",
    )

    objects = GuardManager()

    class Meta:

        db_table = "guards"

        ordering = [
            "township",
            "employee_code",
        ]

        verbose_name = "نگهبان"

        verbose_name_plural = "نگهبان‌ها"

        indexes = [

            models.Index(
                fields=["township", "is_active"],
                name="idx_guard_township_active",
            ),

        ]

    def __str__(self):

        display_name = self.user.get_full_name() or self.user.username

        return f"{display_name} ({self.employee_code})"

    def save(self, *args, **kwargs):

        if self.employee_code:

            self.employee_code = self.employee_code.strip().upper()

        super().save(*args, **kwargs)

    @property
    def has_active_shift(self):

        return self.shifts.filter(
            ended_at__isnull=True,
        ).exists()

    @property
    def current_shift(self):

        return self.shifts.filter(
            ended_at__isnull=True,
        ).first()


class GuardShift(BaseModel):
    """
    ثبت واقعی شروع/پایان حضور نگهبان (Clock-in / Clock-out).
    هر نگهبان در هر لحظه فقط یک شیفت باز (ended_at خالی) می‌تواند داشته باشد؛
    این قانون هم در Service و هم به صورت Constraint در سطح دیتابیس تضمین شده است.
    """

    guard = models.ForeignKey(
        Guard,
        on_delete=models.CASCADE,
        related_name="shifts",
        verbose_name="نگهبان",
    )

    started_at = models.DateTimeField(
        verbose_name="زمان شروع",
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان پایان",
    )

    class Meta:

        db_table = "guard_shifts"

        ordering = [
            "-started_at",
        ]

        verbose_name = "شیفت نگهبان"

        verbose_name_plural = "شیفت‌های نگهبان"

        constraints = [

            models.UniqueConstraint(
                fields=["guard"],
                condition=models.Q(ended_at__isnull=True),
                name="unique_open_shift_per_guard",
            ),

            models.CheckConstraint(
                condition=(
                    models.Q(ended_at__isnull=True)
                    | models.Q(ended_at__gt=models.F("started_at"))
                ),
                name="guard_shift_end_after_start",
            ),

        ]

    def __str__(self):

        return f"{self.guard} | {self.started_at:%Y-%m-%d %H:%M}"

    @property
    def is_open(self):

        return self.ended_at is None

    @property
    def duration(self):

        if self.ended_at is None:

            return None

        return self.ended_at - self.started_at


class GuardLog(BaseModel):
    """
    تاریخچه رویدادهای نگهبان: ورود/خروج به سیستم، ثبت تردد، و عملیات دستی مدیر.
    """

    class Action(models.TextChoices):

        LOGIN = "LOGIN", "ورود"

        LOGOUT = "LOGOUT", "خروج"

        CHECKIN = "CHECKIN", "ثبت ورود"

        CHECKOUT = "CHECKOUT", "ثبت خروج"

        GATE_ASSIGNED = "GATE_ASSIGNED", "تخصیص درب"

        GATE_REMOVED = "GATE_REMOVED", "حذف تخصیص درب"

        ACTIVATED = "ACTIVATED", "فعال‌سازی"

        DEACTIVATED = "DEACTIVATED", "غیرفعال‌سازی"

        MANUAL = "MANUAL", "عملیات دستی"

    guard = models.ForeignKey(
        Guard,
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name="نگهبان",
    )

    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        verbose_name="عملیات",
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guard_logs_performed",
        verbose_name="انجام‌شده توسط",
    )

    description = models.TextField(
        blank=True,
        verbose_name="توضیحات",
    )

    class Meta:

        db_table = "guard_logs"

        ordering = [
            "-created_at",
        ]

        verbose_name = "رویداد نگهبان"

        verbose_name_plural = "رویدادهای نگهبان"

    def __str__(self):

        return f"{self.guard} - {self.action}"
