from django.db import transaction

from django.utils import timezone

from rest_framework.exceptions import ValidationError

from .models import (
    Guard,
    GuardLog,
    GuardShift,
)


class GuardService:
    """
    تمام تغییرات وضعیت نگهبان (شیفت، فعال‌سازی، تخصیص درب) باید فقط از
    طریق این سرویس انجام شود تا تاریخچه (GuardLog) همیشه ثبت شود.
    """

    # ==================================================
    # شیفت حضور (Clock-in / Clock-out)
    # ==================================================

    @staticmethod
    @transaction.atomic
    def start_shift(
        guard,
        performed_by=None,
    ):

        if not guard.is_active:

            raise ValidationError(
                "نگهبان غیرفعال است و نمی‌تواند شیفت را شروع کند.",
            )

        if guard.has_active_shift:

            raise ValidationError(
                "این نگهبان از قبل یک شیفت باز دارد.",
            )

        shift = GuardShift.objects.create(
            guard=guard,
            started_at=timezone.now(),
        )

        GuardLog.objects.create(
            guard=guard,
            action=GuardLog.Action.LOGIN,
            performed_by=performed_by or guard.user,
            description="شروع شیفت",
        )

        return shift

    @staticmethod
    @transaction.atomic
    def end_shift(
        guard,
        performed_by=None,
    ):

        shift = guard.current_shift

        if shift is None:

            raise ValidationError(
                "شیفت فعالی برای این نگهبان وجود ندارد.",
            )

        shift.ended_at = timezone.now()

        shift.save(
            update_fields=[
                "ended_at",
                "updated_at",
            ],
        )

        GuardLog.objects.create(
            guard=guard,
            action=GuardLog.Action.LOGOUT,
            performed_by=performed_by or guard.user,
            description="پایان شیفت",
        )

        return shift

    # ==================================================
    # فعال‌سازی / غیرفعال‌سازی نگهبان
    # ==================================================

    @staticmethod
    @transaction.atomic
    def activate(
        guard,
        performed_by=None,
    ):

        if guard.is_active:

            raise ValidationError(
                "این نگهبان از قبل فعال است.",
            )

        guard.is_active = True

        guard.save(
            update_fields=[
                "is_active",
                "updated_at",
            ],
        )

        GuardLog.objects.create(
            guard=guard,
            action=GuardLog.Action.ACTIVATED,
            performed_by=performed_by,
            description="فعال‌سازی نگهبان",
        )

        return guard

    @staticmethod
    @transaction.atomic
    def deactivate(
        guard,
        performed_by=None,
    ):

        if not guard.is_active:

            raise ValidationError(
                "این نگهبان از قبل غیرفعال است.",
            )

        guard.is_active = False

        guard.save(
            update_fields=[
                "is_active",
                "updated_at",
            ],
        )

        if guard.has_active_shift:

            GuardService.end_shift(
                guard=guard,
                performed_by=performed_by,
            )

        GuardLog.objects.create(
            guard=guard,
            action=GuardLog.Action.DEACTIVATED,
            performed_by=performed_by,
            description="غیرفعال‌سازی نگهبان",
        )

        return guard

    # ==================================================
    # تخصیص / حذف درب
    # ==================================================

    @staticmethod
    @transaction.atomic
    def assign_gate(
        guard,
        gate,
        performed_by=None,
    ):

        if gate.township_id != guard.township_id:

            raise ValidationError(
                "درب انتخاب‌شده متعلق به شهرک این نگهبان نیست.",
            )

        if guard.gates.filter(
            pk=gate.pk,
        ).exists():

            raise ValidationError(
                "این درب از قبل به این نگهبان تخصیص داده شده است.",
            )

        guard.gates.add(gate)

        GuardLog.objects.create(
            guard=guard,
            action=GuardLog.Action.GATE_ASSIGNED,
            performed_by=performed_by,
            description=f"تخصیص درب {gate.code}",
        )

        return guard

    @staticmethod
    @transaction.atomic
    def remove_gate(
        guard,
        gate,
        performed_by=None,
    ):

        if not guard.gates.filter(
            pk=gate.pk,
        ).exists():

            raise ValidationError(
                "این درب به این نگهبان تخصیص داده نشده است.",
            )

        guard.gates.remove(gate)

        GuardLog.objects.create(
            guard=guard,
            action=GuardLog.Action.GATE_REMOVED,
            performed_by=performed_by,
            description=f"حذف تخصیص درب {gate.code}",
        )

        return guard

    # ==================================================
    # ثبت رویداد دستی (مثلاً یادداشت مدیر)
    # ==================================================

    @staticmethod
    def log_manual_event(
        guard,
        description,
        performed_by=None,
    ):

        return GuardLog.objects.create(
            guard=guard,
            action=GuardLog.Action.MANUAL,
            performed_by=performed_by,
            description=description,
        )
