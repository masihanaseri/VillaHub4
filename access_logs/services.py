from django.db import transaction

from rest_framework.exceptions import ValidationError

from .models import AccessLog

from .validators import (
    validate_gate_guard_township,
    validate_subject_exclusivity,
)


class AccessLogService:
    """
    تمام رکوردهای تردد باید از طریق این سرویس ثبت شوند تا:
      - همخوانی township/gate/guard تضمین شود.
      - وضعیت Visitor (در visitors app) به‌صورت خودکار همگام بماند.
    این سرویس فقط عملیات create دارد؛ AccessLog پس از ثبت تغییرناپذیر است.
    """

    @staticmethod
    def _resolve_township(gate):

        return gate.township

    @staticmethod
    @transaction.atomic
    def record(
        gate,
        direction,
        guard=None,
        visitor=None,
        residence=None,
        access_method=AccessLog.AccessMethod.MANUAL,
        plate_number="",
        notes="",
        occurred_at=None,
    ):

        if gate is None:

            raise ValidationError(
                "درب الزامی است.",
            )

        if not gate.is_active:

            raise ValidationError(
                "این درب غیرفعال است و امکان ثبت تردد از آن وجود ندارد.",
            )

        validate_gate_guard_township(
            gate=gate,
            guard=guard,
        )

        validate_subject_exclusivity(
            visitor=visitor,
            residence=residence,
        )

        if visitor is not None and visitor.township_id != gate.township_id:

            raise ValidationError(
                "این مهمان متعلق به شهرک این درب نیست.",
            )

        if residence is not None and residence.villa.township_id != gate.township_id:

            raise ValidationError(
                "این ساکن متعلق به شهرک این درب نیست.",
            )

        access_log = AccessLog.objects.create(
            township=AccessLogService._resolve_township(gate),
            gate=gate,
            guard=guard,
            visitor=visitor,
            residence=residence,
            direction=direction,
            access_method=access_method,
            plate_number=plate_number,
            notes=notes,
            **({"occurred_at": occurred_at} if occurred_at else {}),
        )

        if visitor is not None:

            AccessLogService._sync_visitor_status(
                visitor=visitor,
                direction=direction,
            )

        return access_log

    @staticmethod
    def record_entry(
        gate,
        guard=None,
        visitor=None,
        residence=None,
        access_method=AccessLog.AccessMethod.MANUAL,
        plate_number="",
        notes="",
    ):

        return AccessLogService.record(
            gate=gate,
            direction=AccessLog.Direction.IN,
            guard=guard,
            visitor=visitor,
            residence=residence,
            access_method=access_method,
            plate_number=plate_number,
            notes=notes,
        )

    @staticmethod
    def record_exit(
        gate,
        guard=None,
        visitor=None,
        residence=None,
        access_method=AccessLog.AccessMethod.MANUAL,
        plate_number="",
        notes="",
    ):

        return AccessLogService.record(
            gate=gate,
            direction=AccessLog.Direction.OUT,
            guard=guard,
            visitor=visitor,
            residence=residence,
            access_method=access_method,
            plate_number=plate_number,
            notes=notes,
        )

    @staticmethod
    def _sync_visitor_status(visitor, direction):
        """
        همگام‌سازی وضعیت Visitor با تردد ثبت‌شده.
        اگر مهمان از قبل در وضعیت مناسب برای check_in/check_out نباشد
        (مثلاً هنوز تایید نشده)، AccessLog همچنان ثبت می‌شود اما همگام‌سازی
        نادیده گرفته می‌شود؛ چون رد کردن کل تردد فیزیکی به‌خاطر یک اختلاف
        وضعیت اداری، تصمیم درستی برای درب امنیتی نیست.
        """

        from visitors.services import VisitorService

        try:

            if direction == AccessLog.Direction.IN:

                VisitorService.check_in(visitor)

            else:

                VisitorService.check_out(visitor)

        except ValidationError:

            pass
