from django.db import models

from core.models import BaseModel

from .managers import GateManager

from .validators import (
    validate_gate_code,
    validate_latitude,
    validate_longitude,
)


class Gate(BaseModel):
    """
    درب‌های تردد یک شهرک (ورودی/خروجی خودرو یا پیاده).
    این مدل نقطه اتصال Visitor و Guard به یکدیگر است:

        Visitor -> Gate -> Guard -> AccessLog (بعداً اضافه می‌شود)
    """

    township = models.ForeignKey(
        "townships.Township",
        on_delete=models.CASCADE,
        related_name="gates",
        verbose_name="شهرک",
    )

    name = models.CharField(
        max_length=150,
        verbose_name="نام درب",
    )

    code = models.CharField(
        max_length=30,
        validators=[validate_gate_code],
        verbose_name="کد درب",
        help_text="کد یکتای درب در سطح شهرک (مثال: GATE-01)",
    )

    description = models.TextField(
        blank=True,
        verbose_name="توضیحات",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال",
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

    objects = GateManager()

    class Meta:

        db_table = "gates"

        ordering = [
            "township",
            "name",
        ]

        verbose_name = "درب"

        verbose_name_plural = "درب‌ها"

        constraints = [

            models.UniqueConstraint(
                fields=["township", "code"],
                name="unique_gate_code_per_township",
            ),

            models.CheckConstraint(
                condition=(
                    models.Q(latitude__isnull=True, longitude__isnull=True)
                    | models.Q(latitude__isnull=False, longitude__isnull=False)
                ),
                name="gate_lat_lng_both_or_none",
            ),

        ]

        indexes = [

            models.Index(
                fields=["township", "is_active"],
                name="idx_gate_township_active",
            ),

            models.Index(
                fields=["township", "code"],
                name="idx_gate_township_code",
            ),

        ]

    def __str__(self):

        return (
            f"{self.township.name} | "
            f"{self.name} "
            f"({self.code})"
        )

    def save(self, *args, **kwargs):

        if self.code:

            self.code = self.code.strip().upper()

        super().save(*args, **kwargs)

    @property
    def has_coordinates(self):

        return (
            self.latitude is not None
            and self.longitude is not None
        )

    @property
    def coordinates(self):

        if not self.has_coordinates:

            return None

        return (
            float(self.latitude),
            float(self.longitude),
        )
