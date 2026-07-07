from django.db import transaction

from django.utils import timezone

from rest_framework.exceptions import ValidationError

from .models import (
    Visitor,
    VisitorLog,
    VisitorVehicle,
)

class VisitorService:
    @staticmethod
    @transaction.atomic
    def create(

        created_by,

        **validated_data,

    ):

        visitor = Visitor.objects.create(

            created_by=created_by,

            township=created_by.active_township,

            **validated_data,

        )

        VisitorLog.objects.create(

            visitor=visitor,

            action="CREATED",

            user=created_by,

            description="ثبت درخواست مهمان",

        )

        return visitor
    @staticmethod
    @transaction.atomic
    def approve(

        visitor,

        approved_by,

    ):

        if visitor.status != "REQUESTED":

            raise ValidationError(

                "فقط درخواست‌های جدید قابل تایید هستند."

            )

        visitor.status = Visitor.VisitorStatus.APPROVED

        visitor.approved_by = approved_by

        visitor.approved_at = timezone.now()

        visitor.save()

        VisitorLog.objects.create(

            visitor=visitor,

            action="APPROVED",

            user=approved_by,

            description="تایید مهمان",

        )

        return visitor
    @staticmethod
    @transaction.atomic
    def reject(

        visitor,

        rejected_by,

        reason="",

    ):

        visitor.status = Visitor.VisitorStatus.REJECTED

        visitor.save()

        VisitorLog.objects.create(

            visitor=visitor,

            action="REJECTED",

            user=rejected_by,

            description=reason,

        )

        return visitor
    @staticmethod
    @transaction.atomic
    def cancel(

        visitor,

        cancelled_by,

        reason="",

    ):

        visitor.status = Visitor.VisitorStatus.CANCELLED

        visitor.save()

        VisitorLog.objects.create(

            visitor=visitor,

            action="CANCELLED",

            user=cancelled_by,

            description=reason,

        )

        return visitor
    @staticmethod
    @transaction.atomic
    def check_in(

        visitor,

    ):

        if visitor.status != "APPROVED":

            raise ValidationError(

                "مهمان هنوز تایید نشده است."

            )

        visitor.status = Visitor.VisitorStatus.CHECKED_IN

        visitor.checked_in_at = timezone.now()

        visitor.save()

        VisitorLog.objects.create(

            visitor=visitor,

            action="CHECK_IN",

            user=visitor.created_by,

            description="ورود مهمان",

        )

        return visitor
    @staticmethod
    @transaction.atomic
    def check_out(

        visitor,

    ):

        if visitor.status != "CHECKED_IN":

            raise ValidationError(

                "مهمان وارد شهرک نشده است."

            )

        visitor.status = Visitor.VisitorStatus.CHECKED_OUT

        visitor.checked_out_at = timezone.now()

        visitor.save()

        VisitorLog.objects.create(

            visitor=visitor,

            action="CHECK_OUT",

            user=visitor.created_by,

            description="خروج مهمان",

        )

        return visitor
    @staticmethod
    @transaction.atomic
    def add_vehicle(

        visitor,

        plate_number,

        car_model="",

        color="",

    ):

        vehicle = VisitorVehicle.objects.create(

            visitor=visitor,

            plate_number=plate_number,

            car_model=car_model,

            color=color,

        )

        VisitorLog.objects.create(

            visitor=visitor,

            action="EDITED",

            user=visitor.created_by,

            description=f"ثبت خودرو با پلاک {plate_number}",

        )

        return vehicle
    @staticmethod
    def expire():

        Visitor.objects.filter(

            status="APPROVED",

            valid_until__lt=timezone.now(),

        ).update(

            status=Visitor.VisitorStatus.EXPIRED,

        )
