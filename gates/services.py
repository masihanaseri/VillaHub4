from django.db import transaction
from django.db.utils import IntegrityError

from rest_framework.exceptions import ValidationError

from .models import Gate


class GateService:
    """
    تمام منطق تغییر وضعیت و ایجاد درب باید از طریق این سرویس انجام شود.
    ViewSet و Serializer نباید مستقیماً روی Gate.objects.create/save عمل کنند.
    """

    @staticmethod
    @transaction.atomic
    def create(
        township,
        name,
        code,
        description="",
        is_active=True,
        latitude=None,
        longitude=None,
    ):

        if township is None:

            raise ValidationError(
                "برای ایجاد درب باید یک شهرک فعال انتخاب شده باشد.",
            )

        try:

            gate = Gate.objects.create(
                township=township,
                name=name,
                code=code,
                description=description,
                is_active=is_active,
                latitude=latitude,
                longitude=longitude,
            )

        except IntegrityError:

            raise ValidationError(
                "درِ دیگری با همین کد در این شهرک ثبت شده است.",
            )

        return gate

    @staticmethod
    @transaction.atomic
    def update(
        gate,
        **fields,
    ):

        allowed_fields = {
            "name",
            "code",
            "description",
            "latitude",
            "longitude",
        }

        unknown_fields = set(fields) - allowed_fields

        if unknown_fields:

            raise ValidationError(
                f"فیلدهای غیرمجاز برای ویرایش: {', '.join(sorted(unknown_fields))}",
            )

        for field_name, value in fields.items():

            setattr(gate, field_name, value)

        try:

            gate.full_clean()

            gate.save()

        except IntegrityError:

            raise ValidationError(
                "درِ دیگری با همین کد در این شهرک ثبت شده است.",
            )

        return gate

    @staticmethod
    @transaction.atomic
    def activate(
        gate,
    ):

        if gate.is_active:

            raise ValidationError(
                "این درب از قبل فعال است.",
            )

        gate.is_active = True

        gate.save(
            update_fields=[
                "is_active",
                "updated_at",
            ],
        )

        return gate

    @staticmethod
    @transaction.atomic
    def deactivate(
        gate,
    ):

        if not gate.is_active:

            raise ValidationError(
                "این درب از قبل غیرفعال است.",
            )

        gate.is_active = False

        gate.save(
            update_fields=[
                "is_active",
                "updated_at",
            ],
        )

        return gate

    @staticmethod
    def deactivate_all_for_township(
        township,
    ):
        """
        غیرفعال‌سازی گروهی تمام درب‌های یک شهرک.
        مثلاً هنگامی که خود شهرک غیرفعال می‌شود استفاده خواهد شد.
        """

        return Gate.objects.for_township(
            township,
        ).active().update(
            is_active=False,
        )
