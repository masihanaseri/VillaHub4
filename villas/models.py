from django.db import models
from core.models import BaseModel
from django.contrib.auth import get_user_model

User = get_user_model()

class Villa(BaseModel):

    township = models.ForeignKey(
        "townships.Township",
        on_delete=models.CASCADE,
        related_name="villas",
    )

    code = models.CharField(
        max_length=30,
    )

    name = models.CharField(
        max_length=150,
    )

    area = models.DecimalField(
        max_digits=8,
        decimal_places=2,
    )

    is_active = models.BooleanField(
        default=True,
    )

    description = models.TextField(
        blank=True,
    )

    class Meta:

        db_table = "villas"

        ordering = ["code"]

        verbose_name = "ویلا"

        verbose_name_plural = "ویلاها"

        constraints = [
            models.UniqueConstraint(
                fields=["township", "code"],
                name="unique_villa_code_per_township",
            ),
        ]

    def __str__(self):
      return f"{self.code} - {self.name}"

class Residence(BaseModel):

    class ResidentType(models.TextChoices):

        OWNER = "OWNER", "مالک"
        TENANT = "TENANT", "مستأجر"
        FAMILY = "FAMILY", "عضو خانواده"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="residences",
    )

    villa = models.ForeignKey(
        Villa,
        on_delete=models.CASCADE,
        related_name="residences",
    )

    resident_type = models.CharField(
        max_length=20,
        choices=ResidentType.choices,
    )

    start_date = models.DateField()

    end_date = models.DateField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    family_count = models.PositiveSmallIntegerField(
    default=1,
    verbose_name="تعداد افراد ساکن",
    help_text="شامل مالک یا مستأجر نیز می‌شود.",
)

    class Meta:

        db_table = "residences"

        ordering = ["villa", "-start_date"]

        verbose_name = "سکونت"

        verbose_name_plural = "سکونت‌ها"

        constraints = [
            models.UniqueConstraint(
                fields=["user", "villa", "resident_type", "start_date"],
                name="unique_residence_record",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} | {self.villa.code} | {self.get_resident_type_display()}"