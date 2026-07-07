from django.db import models
from django.conf import settings
from .managers import ReservationManager
from core.models import BaseModel
from django.utils import timezone

class ReservationSlot(BaseModel):
    """
    سانس‌های قابل رزرو هر امکان
    """

    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.CASCADE,
        related_name="slots",
    )

    title = models.CharField(
        max_length=100,
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    capacity = models.PositiveIntegerField(
        default=1,
    )

    is_active = models.BooleanField(
        default=True,
    )

    sort_order = models.PositiveSmallIntegerField(
        default=1,
    )

    class Meta:

        db_table = "reservation_slots"

        ordering = [
            "sort_order",
            "start_time",
        ]

        verbose_name = "سانس"

        verbose_name_plural = "سانس‌ها"

    def __str__(self):

        return (
            f"{self.facility.name}"
            f" | "
            f"{self.title}"
        )

class Reservation(BaseModel):

    class ReservationStatus(models.TextChoices):

        REQUESTED = "REQUESTED", "درخواست شده"
        APPROVED = "APPROVED", "تأیید شده"
        REJECTED = "REJECTED", "رد شده"
        CANCELLED = "CANCELLED", "لغو شده"
        COMPLETED = "COMPLETED", "پایان یافته"

    class PaymentStatus(models.TextChoices):

        UNPAID = "UNPAID", "پرداخت نشده"
        PARTIAL = "PARTIAL", "پرداخت ناقص"
        PAID = "PAID", "پرداخت شده"
        REFUNDED = "REFUNDED", "عودت داده شده"

    reservation_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
    )

    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="reservations",
    ) 

    slot = models.ForeignKey(
        ReservationSlot,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reservations",
    )

    residence = models.ForeignKey(
        "villas.Residence",
        on_delete=models.PROTECT,
        related_name="reservations",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_reservations",
    )

    start_datetime = models.DateTimeField()

    end_datetime = models.DateTimeField()

    guest_count = models.PositiveIntegerField(
        default=1,
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )    

    reservation_status = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.REQUESTED,
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )

    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    remaining_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )    

    price_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    deposit_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_reservations",
    )

    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cancelled_reservations",
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )    

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancel_reason = models.TextField(
        blank=True,
    )

    admin_note = models.TextField(
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    checked_in_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    checked_out_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    late_minutes = models.PositiveIntegerField(
        default=0,
    )

    extra_charge = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )        

    objects = ReservationManager()

    class Meta:

        db_table = "reservations"

        ordering = [
            "-start_datetime",
        ]

        verbose_name = "رزرو"

        verbose_name_plural = "رزروها"

    def __str__(self):

        return (
            f"{self.facility.name} | "
            f"{self.residence.villa.code} | "
            f"{self.start_datetime}"
        )
    
    def delete(self, *args, **kwargs):

        raise ValueError(
            "حذف رزرو مجاز نیست."
        )

    @property
    def is_finished(self):

        return (

            self.reservation_status

            ==

            self.ReservationStatus.COMPLETED

        )


    @property
    def is_cancelled(self):

        return (

            self.reservation_status

            ==

            self.ReservationStatus.CANCELLED

        )


    @property
    def is_paid_full(self):

        return (

            self.payment_status

            ==

            self.PaymentStatus.PAID

        )


    @property
    def duration(self):

        return (

            self.end_datetime

            - self.start_datetime

        )       
    
class ReservationLog(BaseModel):
    """
    تاریخچه تغییرات رزرو
    """

    class Action(models.TextChoices):

        CREATED = "CREATED", "ایجاد"

        APPROVED = "APPROVED", "تایید"

        CANCELLED = "CANCELLED", "لغو"

        REJECTED = "REJECTED", "رد"

        EDITED = "EDITED", "ویرایش"

        PAYMENT = "PAYMENT", "پرداخت"

        REFUND = "REFUND", "استرداد"

        AUTO_APPROVED = (
            "AUTO_APPROVED",
            "تایید خودکار",
        )

        ADMIN_APPROVED = (
            "ADMIN_APPROVED",
            "تایید مدیر",
        )

        EXPIRED = (
            "EXPIRED",
            "منقضی",
        )

        ADMIN_CANCELLED = (
            "ADMIN_CANCELLED",
            "لغو توسط مدیر",
        )   

        CHECK_IN = (
            "CHECK_IN",
            "ورود",
        )

        CHECK_OUT = (
            "CHECK_OUT",
            "خروج",
        )

        PARTIAL_PAYMENT = (
            "PARTIAL_PAYMENT",
            "پرداخت ناقص",
        )                  

        FULL_PAYMENT = (
            "FULL_PAYMENT",
            "تسویه کامل",
        )

        REFUND_PAYMENT = (
            "REFUND_PAYMENT",
            "استرداد",
        )

        COMPLETED = (
            "COMPLETED",
            "پایان خودکار",
        )        

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="logs",
    )

    action = models.CharField(
        max_length=20,
        choices=Action.choices,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )

    description = models.TextField(
        blank=True,
    )

    class Meta:

        db_table = "reservation_logs"

        ordering = [
            "-created_at",
        ]

        verbose_name = "تاریخچه رزرو"

        verbose_name_plural = "تاریخچه رزروها"

    def __str__(self):

        return (
            f"{self.reservation.reservation_number}"
            f" - "
            f"{self.action}"
        )

class ReservationPayment(BaseModel):
    """
    پرداخت‌های رزرو
    """

    class PaymentMethod(models.TextChoices):

        CASH = "CASH", "نقدی"

        CARD = "CARD", "کارتخوان"

        ONLINE = "ONLINE", "آنلاین"

        TRANSFER = "TRANSFER", "واریز"

    class PaymentType(models.TextChoices):

        PAYMENT = "PAYMENT", "پرداخت"

        REFUND = "REFUND", "استرداد"

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
    )

    payment_type = models.CharField(
        max_length=20,
        choices=PaymentType.choices,
        default=PaymentType.PAYMENT,
    )

    reference_number = models.CharField(
        max_length=100,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )

    note = models.TextField(
        blank=True,
    )

    class Meta:

        db_table = "reservation_payments"

        ordering = [
            "-created_at",
        ]

        verbose_name = "پرداخت"

        verbose_name_plural = "پرداخت‌ها"

    def __str__(self):

        return (
            f"{self.reservation.reservation_number}"
            f" | "
            f"{self.amount}"
        )
