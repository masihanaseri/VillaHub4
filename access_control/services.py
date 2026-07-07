from django.db import transaction

from django.utils import timezone

from rest_framework.exceptions import ValidationError

from .models import (
    AccessPass,
    AccessLog,
)

from .validators import (
    validate_valid_period,
    validate_visitor_township,
    validate_gate_township,
    validate_guard_township,
)


class AccessControlService:
    """
    تمام تغییرات وضعیت AccessPass و تمام رویدادهای AccessLog باید فقط از
    طریق این سرویس انجام شوند. هیچ منطق تجاری نباید داخل View قرار بگیرد.

    زنجیره کامل معماری:

        Visitor -> AccessPass -> Gate -> Guard -> AccessLog
    """

    # ==================================================
    # ایجاد کارت تردد
    # ==================================================

    @staticmethod
    @transaction.atomic
    def create_access_pass(
        *,
        visitor,
        created_by,
        valid_from,
        valid_until,
        gate=None,
        notes="",
    ):

        if visitor is None:

            raise ValidationError(
                "انتخاب مهمان الزامی است.",
            )

        township = visitor.township

        validate_valid_period(
            valid_from,
            valid_until,
        )

        validate_gate_township(
            gate,
            township,
        )

        access_pass = AccessPass.objects.create(
            township=township,
            visitor=visitor,
            gate=gate,
            created_by=created_by,
            valid_from=valid_from,
            valid_until=valid_until,
            notes=notes,
            status=AccessPass.Status.PENDING,
        )

        return access_pass

    # ==================================================
    # تایید کارت تردد
    # ==================================================

    @staticmethod
    @transaction.atomic
    def approve(
        *,
        access_pass,
        approved_by,
        note="",
    ):

        access_pass = AccessPass.objects.select_for_update().get(
            pk=access_pass.pk,
        )

        if access_pass.status != AccessPass.Status.PENDING:

            raise ValidationError(
                "فقط کارت‌های در انتظار تایید قابل تایید هستند.",
            )

        if access_pass.is_expired:

            raise ValidationError(
                "این کارت تردد منقضی شده و قابل تایید نیست.",
            )

        access_pass.status = AccessPass.Status.APPROVED

        access_pass.approved_by = approved_by

        access_pass.approved_at = timezone.now()

        if note:

            access_pass.notes = note

        access_pass.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
                "notes",
                "updated_at",
            ]
        )

        return access_pass

    # ==================================================
    # رد کارت تردد
    # ==================================================

    @staticmethod
    @transaction.atomic
    def reject(
        *,
        access_pass,
        rejected_by,
        reason="",
    ):

        access_pass = AccessPass.objects.select_for_update().get(
            pk=access_pass.pk,
        )

        if access_pass.status != AccessPass.Status.PENDING:

            raise ValidationError(
                "فقط کارت‌های در انتظار تایید قابل رد هستند.",
            )

        access_pass.status = AccessPass.Status.REJECTED

        if reason:

            access_pass.notes = reason

        access_pass.save(
            update_fields=[
                "status",
                "notes",
                "updated_at",
            ]
        )

        return access_pass

    # ==================================================
    # لغو کارت تردد
    # ==================================================

    @staticmethod
    @transaction.atomic
    def cancel(
        *,
        access_pass,
        cancelled_by,
        reason="",
    ):

        access_pass = AccessPass.objects.select_for_update().get(
            pk=access_pass.pk,
        )

        if access_pass.status in [

            AccessPass.Status.CANCELLED,

            AccessPass.Status.REJECTED,

            AccessPass.Status.CHECKED_OUT,

            AccessPass.Status.EXPIRED,

        ]:

            raise ValidationError(
                "این کارت تردد قابل لغو نیست.",
            )

        access_pass.status = AccessPass.Status.CANCELLED

        if reason:

            access_pass.notes = reason

        access_pass.save(
            update_fields=[
                "status",
                "notes",
                "updated_at",
            ]
        )

        return access_pass

    # ==================================================
    # اعتبارسنجی QR (فقط بررسی، بدون تغییر وضعیت)
    # ==================================================

    @staticmethod
    @transaction.atomic
    def validate_qr(
        *,
        qr_token,
        gate,
        guard=None,
        device="",
        latitude=None,
        longitude=None,
        ip_address=None,
    ):
        """
        یک کد QR اسکن‌شده توسط نگهبان را اعتبارسنجی می‌کند. این تابع فقط
        صحت کارت را بررسی و رویداد اسکن را ثبت می‌کند؛ ورود واقعی باید
        جداگانه از طریق check_in انجام شود.
        """

        try:

            access_pass = AccessPass.objects.select_for_update().get(
                qr_token=qr_token,
            )

        except AccessPass.DoesNotExist:

            raise ValidationError(
                "کد QR نامعتبر است یا کارت تردد یافت نشد.",
            )

        validate_guard_township(
            guard,
            access_pass.township,
        )

        if not access_pass.is_valid:

            AccessControlService.create_access_log(
                access_pass=access_pass,
                gate=gate,
                guard=guard,
                action=AccessLog.Action.DENIED,
                device=device,
                latitude=latitude,
                longitude=longitude,
                ip_address=ip_address,
                notes="کارت تردد معتبر نیست (وضعیت یا بازه زمانی نامعتبر).",
            )

            raise ValidationError(
                "این کارت تردد معتبر نیست (وضعیت یا بازه زمانی نامعتبر).",
            )

        if access_pass.gate_id and gate is not None and access_pass.gate_id != gate.id:

            AccessControlService.create_access_log(
                access_pass=access_pass,
                gate=gate,
                guard=guard,
                action=AccessLog.Action.DENIED,
                device=device,
                latitude=latitude,
                longitude=longitude,
                ip_address=ip_address,
                notes="این کارت تردد برای درب دیگری صادر شده است.",
            )

            raise ValidationError(
                "این کارت تردد فقط برای درب مشخص‌شده معتبر است.",
            )

        AccessControlService.create_access_log(
            access_pass=access_pass,
            gate=gate,
            guard=guard,
            action=AccessLog.Action.QR_SCAN,
            device=device,
            latitude=latitude,
            longitude=longitude,
            ip_address=ip_address,
            notes="کد QR با موفقیت اسکن و اعتبارسنجی شد.",
        )

        return access_pass

    # ==================================================
    # ورود (Check In)
    # ==================================================

    @staticmethod
    @transaction.atomic
    def check_in(
        *,
        access_pass,
        gate,
        guard=None,
        action=AccessLog.Action.MANUAL,
        device="",
        latitude=None,
        longitude=None,
        ip_address=None,
        notes="",
    ):

        access_pass = AccessPass.objects.select_for_update().get(
            pk=access_pass.pk,
        )

        validate_gate_township(
            gate,
            access_pass.township,
        )

        validate_guard_township(
            guard,
            access_pass.township,
        )

        if not access_pass.is_valid:

            AccessControlService.create_access_log(
                access_pass=access_pass,
                gate=gate,
                guard=guard,
                action=AccessLog.Action.DENIED,
                device=device,
                latitude=latitude,
                longitude=longitude,
                ip_address=ip_address,
                notes=notes or "کارت تردد معتبر نیست.",
            )

            raise ValidationError(
                "این کارت تردد برای ورود معتبر نیست.",
            )

        if access_pass.gate_id and access_pass.gate_id != gate.id:

            AccessControlService.create_access_log(
                access_pass=access_pass,
                gate=gate,
                guard=guard,
                action=AccessLog.Action.DENIED,
                device=device,
                latitude=latitude,
                longitude=longitude,
                ip_address=ip_address,
                notes="این کارت تردد برای درب دیگری صادر شده است.",
            )

            raise ValidationError(
                "این کارت تردد فقط برای درب مشخص‌شده معتبر است.",
            )

        access_pass.status = AccessPass.Status.CHECKED_IN

        access_pass.gate = gate

        access_pass.checked_in_at = timezone.now()

        access_pass.save(
            update_fields=[
                "status",
                "gate",
                "checked_in_at",
                "updated_at",
            ]
        )

        AccessControlService.create_access_log(
            access_pass=access_pass,
            gate=gate,
            guard=guard,
            action=AccessLog.Action.CHECK_IN if action == AccessLog.Action.MANUAL else action,
            device=device,
            latitude=latitude,
            longitude=longitude,
            ip_address=ip_address,
            notes=notes,
        )

        return access_pass

    # ==================================================
    # خروج (Check Out)
    # ==================================================

    @staticmethod
    @transaction.atomic
    def check_out(
        *,
        access_pass,
        gate,
        guard=None,
        device="",
        latitude=None,
        longitude=None,
        ip_address=None,
        notes="",
    ):

        access_pass = AccessPass.objects.select_for_update().get(
            pk=access_pass.pk,
        )

        validate_gate_township(
            gate,
            access_pass.township,
        )

        validate_guard_township(
            guard,
            access_pass.township,
        )

        if access_pass.status != AccessPass.Status.CHECKED_IN:

            AccessControlService.create_access_log(
                access_pass=access_pass,
                gate=gate,
                guard=guard,
                action=AccessLog.Action.DENIED,
                device=device,
                latitude=latitude,
                longitude=longitude,
                ip_address=ip_address,
                notes=notes or "این کارت تردد ورود ثبت‌شده‌ای ندارد.",
            )

            raise ValidationError(
                "فقط کارت‌هایی که ورودشان ثبت شده قابل خروج هستند.",
            )

        access_pass.status = AccessPass.Status.CHECKED_OUT

        access_pass.checked_out_at = timezone.now()

        access_pass.save(
            update_fields=[
                "status",
                "checked_out_at",
                "updated_at",
            ]
        )

        AccessControlService.create_access_log(
            access_pass=access_pass,
            gate=gate,
            guard=guard,
            action=AccessLog.Action.CHECK_OUT,
            device=device,
            latitude=latitude,
            longitude=longitude,
            ip_address=ip_address,
            notes=notes,
        )

        return access_pass

    # ==================================================
    # اقدام مدیر (Override دستی)
    # ==================================================

    @staticmethod
    @transaction.atomic
    def manager_override(
        *,
        access_pass,
        gate,
        manager,
        target_status,
        notes="",
    ):
        """
        اجازه می‌دهد یک مدیر شهرک، مستقل از قوانین معمول تایید/بازه زمانی،
        وضعیت یک کارت تردد را به CHECKED_IN یا CHECKED_OUT تغییر دهد. این
        اقدام همیشه با action=MANAGER در AccessLog ثبت می‌شود.
        """

        access_pass = AccessPass.objects.select_for_update().get(
            pk=access_pass.pk,
        )

        validate_gate_township(
            gate,
            access_pass.township,
        )

        if target_status not in [
            AccessPass.Status.CHECKED_IN,
            AccessPass.Status.CHECKED_OUT,
        ]:

            raise ValidationError(
                "اقدام مدیر فقط برای ثبت ورود یا خروج مجاز است.",
            )

        access_pass.status = target_status

        access_pass.gate = gate

        if target_status == AccessPass.Status.CHECKED_IN:

            access_pass.checked_in_at = timezone.now()

            update_fields = [
                "status",
                "gate",
                "checked_in_at",
                "updated_at",
            ]

        else:

            access_pass.checked_out_at = timezone.now()

            update_fields = [
                "status",
                "gate",
                "checked_out_at",
                "updated_at",
            ]

        access_pass.save(
            update_fields=update_fields,
        )

        AccessControlService.create_access_log(
            access_pass=access_pass,
            gate=gate,
            guard=None,
            action=AccessLog.Action.MANAGER,
            notes=notes or f"اقدام دستی مدیر ({manager}).",
        )

        return access_pass

    # ==================================================
    # ثبت رویداد در دفترچه ممیزی
    # ==================================================

    @staticmethod
    def create_access_log(
        *,
        access_pass,
        gate,
        action,
        guard=None,
        device="",
        latitude=None,
        longitude=None,
        ip_address=None,
        notes="",
    ):

        if gate is None:

            raise ValidationError(
                "درب الزامی است.",
            )

        validate_gate_township(
            gate,
            access_pass.township,
        )

        validate_guard_township(
            guard,
            access_pass.township,
        )

        return AccessLog.objects.create(
            township=access_pass.township,
            access_pass=access_pass,
            gate=gate,
            guard=guard,
            action=action,
            device=device,
            latitude=latitude,
            longitude=longitude,
            ip_address=ip_address,
            notes=notes,
        )

    # ==================================================
    # انقضای خودکار کارت‌های تردد
    # ==================================================

    @staticmethod
    @transaction.atomic
    def expire_passes():
        """
        تمام کارت‌های PENDING/APPROVED که بازه اعتبارشان گذشته را به
        EXPIRED تغییر می‌دهد. مناسب برای اجرای دوره‌ای (cron/management
        command).
        """

        queryset = AccessPass.objects.filter(
            status__in=[
                AccessPass.Status.PENDING,
                AccessPass.Status.APPROVED,
            ],
            valid_until__lt=timezone.now(),
        )

        return queryset.update(
            status=AccessPass.Status.EXPIRED,
        )
