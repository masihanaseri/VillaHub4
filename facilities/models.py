from django.db import models

from core.models import BaseModel


class Facility(BaseModel):

    class ReservationUnit(models.TextChoices):

        HOUR = "HOUR", "ساعتی"

        DAY = "DAY", "روزانه"

    class ReservationPolicy(models.TextChoices):

        EXCLUSIVE = (
            "EXCLUSIVE",
            "فقط یک رزرو",
        )

        PER_VILLA = (
            "PER_VILLA",
            "هر ویلا یک رزرو",
        )

        CAPACITY = (
            "CAPACITY",
            "بر اساس ظرفیت",
        )

        

    class BookingMode(models.TextChoices):

        TIME = (
            "TIME",
            "بازه زمانی",
        )

        SLOT = (
            "SLOT",
            "سانسی",
        )        

    class PricingPolicy(models.TextChoices):

        PER_RESERVATION = (
            "PER_RESERVATION",
            "هر رزرو",
        )

        PER_PERSON = (
            "PER_PERSON",
            "هر نفر",
        )

        PER_HOUR = (
            "PER_HOUR",
            "هر ساعت",
        )

        PER_DAY = (
            "PER_DAY",
            "هر روز",
        )

    township = models.ForeignKey(
        "townships.Township",
        on_delete=models.CASCADE,
        related_name="facilities",
    )

    code = models.CharField(
        max_length=30,
    )

    name = models.CharField(
        max_length=150,
    )

    description = models.TextField(
        blank=True,
    )

    capacity = models.PositiveIntegerField(
        default=1,
    )

    reservation_policy = models.CharField(
        max_length=20,
        choices=ReservationPolicy.choices,
        default=ReservationPolicy.EXCLUSIVE,
        verbose_name="روش رزرو",
    )

    booking_mode = models.CharField(
        max_length=10,
        choices=BookingMode.choices,
        default=BookingMode.TIME,
        verbose_name="نوع رزرو",
    )

    reservation_unit = models.CharField(
        max_length=10,
        choices=ReservationUnit.choices,
        default=ReservationUnit.HOUR,
    )

    reservation_interval = models.PositiveIntegerField(
        default=60,
        help_text="دقیقه",
    )

    is_paid = models.BooleanField(
        default=False,
    )

    pricing_policy = models.CharField(
        max_length=20,
        choices=PricingPolicy.choices,
        default=PricingPolicy.PER_RESERVATION,
        verbose_name="روش محاسبه قیمت",
    )

    minimum_charge = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="حداقل مبلغ قابل دریافت",
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    deposit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    tax_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="درصد مالیات",
    )

    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="درصد تخفیف",
    )

    is_active = models.BooleanField(
        default=True,
    )

    requires_approval = models.BooleanField(
        default=False,
        verbose_name="نیاز به تایید مدیر",
    )

    allow_cancellation = models.BooleanField(
        default=True,
        verbose_name="امکان لغو رزرو",
    )

    cancellation_deadline_hours = models.PositiveSmallIntegerField(
        default=24,
        verbose_name="مهلت لغو (ساعت)",
    )

    max_reservation_duration = models.PositiveSmallIntegerField(
        default=3,
        verbose_name="حداکثر مدت رزرو",
        help_text="بر حسب واحد رزرو",
    )

    available_from = models.TimeField(
        null=True,
        blank=True,
        verbose_name="شروع ساعت کاری",
    )

    available_until = models.TimeField(
        null=True,
        blank=True,
        verbose_name="پایان ساعت کاری",
    )

    max_parallel_reservations = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="حداکثر رزرو همزمان",
    )

    minimum_guest_count = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="حداقل نفرات",
    )

    maximum_guest_count = models.PositiveSmallIntegerField(
        default=999,
        verbose_name="حداکثر نفرات",
    )

    allow_waiting_list = models.BooleanField(
        default=False,
        verbose_name="لیست انتظار",
    )

    class Meta:

        db_table = "facilities"

        ordering = [
            "code",
        ]

        verbose_name = "امکان"

        verbose_name_plural = "امکانات"

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "township",
                    "code",
                ],
                name="unique_facility_code_per_township",
            ),

        ]

    def __str__(self):

        return (
            f"{self.code} - {self.name}"
        )

    @property
    def is_free(self):

        return not self.is_paid


    @property
    def uses_capacity(self):

        return (
            self.reservation_policy
            ==
            self.ReservationPolicy.CAPACITY
        )


    @property
    def uses_per_villa(self):

        return (
            self.reservation_policy
            ==
            self.ReservationPolicy.PER_VILLA
        )


    @property
    def is_exclusive(self):

        return (
            self.reservation_policy
            ==
            self.ReservationPolicy.EXCLUSIVE
        )        