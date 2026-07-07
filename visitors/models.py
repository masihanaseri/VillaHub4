from django.conf import settings

from django.db import models

from core.models import BaseModel

from .managers import VisitorManager

class Visitor(BaseModel):

    class VisitorType(models.TextChoices):

        GUEST = "GUEST", "مهمان"

        CONTRACTOR = "CONTRACTOR", "پیمانکار"

        DELIVERY = "DELIVERY", "پیک"

        SERVICE = "SERVICE", "سرویس"

        STAFF = "STAFF", "پرسنل"

        OTHER = "OTHER", "سایر"

    class VisitorStatus(models.TextChoices):

        REQUESTED = "REQUESTED", "درخواست شده"

        APPROVED = "APPROVED", "تایید شده"

        REJECTED = "REJECTED", "رد شده"

        CANCELLED = "CANCELLED", "لغو شده"

        CHECKED_IN = "CHECKED_IN", "ورود"

        CHECKED_OUT = "CHECKED_OUT", "خروج"

        EXPIRED = "EXPIRED", "منقضی"
    
    township = models.ForeignKey(

        "townships.Township",

        on_delete=models.CASCADE,

        related_name="visitors",

    )

    residence = models.ForeignKey(

        "villas.Residence",

        on_delete=models.CASCADE,

        related_name="visitors",

    )

    created_by = models.ForeignKey(

        settings.AUTH_USER_MODEL,

        on_delete=models.PROTECT,

        related_name="created_visitors",

    )

    visitor_type = models.CharField(

        max_length=20,

        choices=VisitorType.choices,

        default=VisitorType.GUEST,

    )

    full_name = models.CharField(

        max_length=200,

    )

    national_code = models.CharField(

        max_length=20,

        blank=True,

    )

    mobile = models.CharField(

        max_length=20,

    )

    adult_count = models.PositiveIntegerField(

        default=1,

    )

    child_count = models.PositiveIntegerField(

        default=0,

    )

    valid_from = models.DateTimeField()

    valid_until = models.DateTimeField()

    status = models.CharField(

        max_length=20,

        choices=VisitorStatus.choices,

        default=VisitorStatus.REQUESTED,

    )

    purpose = models.CharField(

        max_length=200,

        blank=True,

    )

    notes = models.TextField(

        blank=True,

    )

    approved_by = models.ForeignKey(

        settings.AUTH_USER_MODEL,

        null=True,

        blank=True,

        on_delete=models.SET_NULL,

        related_name="approved_visitors",

    )

    approved_at = models.DateTimeField(

        null=True,

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

    objects = VisitorManager()

    class Meta:

        db_table = "visitors"

        ordering = [

            "-created_at",

        ]

        verbose_name = "مهمان"

        verbose_name_plural = "مهمان‌ها"

    def __str__(self):

        return self.full_name

class VisitorVehicle(BaseModel):

    visitor = models.ForeignKey(

        Visitor,

        on_delete=models.CASCADE,

        related_name="vehicles",

    )

    plate_number = models.CharField(

        max_length=30,

    )

    car_model = models.CharField(

        max_length=100,

        blank=True,

    )

    color = models.CharField(

        max_length=50,

        blank=True,

    )

    class Meta:

        db_table = "visitor_vehicles"

        verbose_name = "خودرو مهمان"

        verbose_name_plural = "خودروهای مهمان"

    def __str__(self):

        return self.plate_number

class VisitorLog(BaseModel):

    class Action(models.TextChoices):

        CREATED = "CREATED", "ایجاد"

        APPROVED = "APPROVED", "تایید"

        REJECTED = "REJECTED", "رد"

        CANCELLED = "CANCELLED", "لغو"

        CHECK_IN = "CHECK_IN", "ورود"

        CHECK_OUT = "CHECK_OUT", "خروج"

        EDITED = "EDITED", "ویرایش"

    visitor = models.ForeignKey(

        Visitor,

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

        db_table = "visitor_logs"

        ordering = [

            "-created_at",

        ]

    def __str__(self):

        return f"{self.visitor.full_name} - {self.action}"      
