from datetime import (
    datetime,
    timedelta,
)
from django.db import transaction
from django.db.models import F
from django.db.models import Q
from django.utils import timezone
from facilities.models import Facility
from .models import (
    Reservation,
    ReservationLog,
    ReservationPayment,
)
from .availability import AvailabilityService
from config import settings


class ReservationService:

    # ==================================================
    # رزروهای همپوشان
    # ==================================================

    @staticmethod
    def overlapping_reservations(
        *,
        facility,
        start_datetime,
        end_datetime,
        exclude_id=None,
    ):

        queryset = Reservation.objects.filter(
            facility=facility,
            reservation_status__in=[
                Reservation.ReservationStatus.REQUESTED,
                Reservation.ReservationStatus.APPROVED,
            ],
        )

        if exclude_id:

            queryset = queryset.exclude(
                pk=exclude_id,
            )

        return queryset.filter(

            start_datetime__lt=end_datetime,

            end_datetime__gt=start_datetime,

        )

    # ==================================================
    # کنترل فعال بودن
    # ==================================================

    @staticmethod
    def validate_active_objects(
        *,
        facility,
        residence,
    ):

        if not facility.is_active:

            raise ValueError(
                "این امکان غیرفعال است."
            )

        if not residence.is_active:

            raise ValueError(
                "سکونت فعال نیست."
            )

        if not residence.villa.is_active:

            raise ValueError(
                "ویلا غیرفعال است."
            )

    # ==================================================
    # کنترل ساعت کاری
    # ==================================================

    @staticmethod
    def validate_working_hours(
        *,
        facility,
        start_datetime,
        end_datetime,
    ):

        if (
            facility.available_from
            and
            facility.available_until
        ):

            start_time = start_datetime.time()

            end_time = end_datetime.time()

            if start_time < facility.available_from:

                raise ValueError(
                    "زمان شروع خارج از ساعت مجاز است."
                )

            if end_time > facility.available_until:

                raise ValueError(
                    "زمان پایان خارج از ساعت مجاز است."
                )

    # ==================================================
    # کنترل مدت رزرو
    # ==================================================

    @staticmethod
    def validate_duration(
        *,
        facility,
        start_datetime,
        end_datetime,
    ):

        if end_datetime <= start_datetime:

            raise ValueError(
                "زمان پایان باید بعد از زمان شروع باشد."
            )

        duration = end_datetime - start_datetime

        if (
            facility.reservation_unit
            ==
            Facility.ReservationUnit.HOUR
        ):

            units = duration.total_seconds() / 3600

        else:

            units = duration.total_seconds() / 86400

        if units > facility.max_reservation_duration:

            raise ValueError(
                f"حداکثر مدت مجاز رزرو {facility.max_reservation_duration} "
                f"{'ساعت' if facility.reservation_unit == Facility.ReservationUnit.HOUR else 'روز'} است."
            )


# ==================================================
# کنترل قوانین رزرو
# ==================================================

    @staticmethod
    def validate_reservation_policy(
        *,
        facility,
        residence,
        start_datetime,
        end_datetime,
        guest_count,
    ):

        # ------------------------------------------
        # تعداد نفرات
        # ------------------------------------------

        if guest_count < facility.minimum_guest_count:

            raise ValueError(
                f"حداقل تعداد نفرات {facility.minimum_guest_count} نفر است."
            )

        if guest_count > facility.maximum_guest_count:

            raise ValueError(
                f"حداکثر تعداد نفرات {facility.maximum_guest_count} نفر است."
            )

        reservations = ReservationService.overlapping_reservations(
            facility=facility,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        )

        # ------------------------------------------
        # فقط یک رزرو
        # ------------------------------------------

        if (
            facility.reservation_policy
            ==
            Facility.ReservationPolicy.EXCLUSIVE
        ):

            if reservations.exists():

                raise ValueError(
                    "این بازه زمانی قبلاً رزرو شده است."
                )

            return

        # ------------------------------------------
        # هر ویلا فقط یک رزرو
        # ------------------------------------------

        if (
            facility.reservation_policy
            ==
            Facility.ReservationPolicy.PER_VILLA
        ):

            if reservations.filter(
                residence__villa=residence.villa
            ).exists():

                raise ValueError(
                    "این ویلا قبلاً در این بازه زمانی رزرو دارد."
                )

            return

        # ------------------------------------------
        # ظرفیت
        # ------------------------------------------

        if (
            facility.reservation_policy
            ==
            Facility.ReservationPolicy.CAPACITY
        ):

            if not AvailabilityService.is_available(

                facility=facility,

                start_datetime=start_datetime,

                end_datetime=end_datetime,

                guest_count=guest_count,

            ):

                raise ValueError(
                    "ظرفیت این بازه زمانی تکمیل شده است."
                )

            return
    # ==================================================
    # محاسبه مبلغ
    # ==================================================

    @staticmethod
    def calculate_price(
        *,
        facility,
        start_datetime,
        end_datetime,
        guest_count,
    ):

        if not facility.is_paid:

            return (
                0,
                0,
                0,
            )

        duration = end_datetime - start_datetime

        if (
            facility.reservation_unit
            ==
            Facility.ReservationUnit.HOUR
        ):

            units = duration.total_seconds() / 3600

        else:

            units = max(
                duration.days,
                1,
            )

        # ------------------------------------
        # مبلغ پایه
        # ------------------------------------

        if (
            facility.pricing_policy
            ==
            Facility.PricingPolicy.PER_RESERVATION
        ):

            subtotal = facility.price

        elif (
            facility.pricing_policy
            ==
            Facility.PricingPolicy.PER_PERSON
        ):

            subtotal = (
                facility.price
                * guest_count
            )

        elif (
            facility.pricing_policy
            ==
            Facility.PricingPolicy.PER_HOUR
        ):

            subtotal = (
                facility.price
                * units
            )

        else:

            subtotal = (
                facility.price
                * units
            )

        # ------------------------------------
        # حداقل مبلغ
        # ------------------------------------

        if subtotal < facility.minimum_charge:

            subtotal = facility.minimum_charge

        # ------------------------------------
        # تخفیف
        # ------------------------------------

        if facility.discount_percent > 0:

            subtotal -= (
                subtotal
                * facility.discount_percent
                / 100
            )

        # ------------------------------------
        # مالیات
        # ------------------------------------

        if facility.tax_percent > 0:

            subtotal += (
                subtotal
                * facility.tax_percent
                / 100
            )

        subtotal = round(
            subtotal,
            2,
        )

        return (

            facility.price,

            facility.deposit,

            subtotal,

        )        
    # ==================================================
    # تولید شماره رزرو
    # ==================================================

    @staticmethod
    def generate_reservation_number(reservation):

        return (

            f"{reservation.facility.code}-"

            f"{timezone.now().strftime('%y%m%d')}-"

            f"{reservation.id:06d}"

        )

    # ==================================================
    # ایجاد رزرو
    # ==================================================

    @staticmethod
    @transaction.atomic
    def create_reservation(
        *,
        facility,
        residence,
        created_by,
        guest_count,
        notes="",
        slot=None,
        start_datetime=None,
        end_datetime=None,
    ):

        facility = (
            Facility.objects
            .select_for_update()
            .get(pk=facility.pk)
        ) 

        # ----------------------------------
        # تعیین زمان رزرو
        # ----------------------------------

        if facility.booking_mode == Facility.BookingMode.SLOT:

            if slot is None:

                raise ValueError(
                    "انتخاب سانس الزامی است."
                )

            if slot.facility_id != facility.id:

                raise ValueError(
                    "سانس متعلق به این امکان نیست."
                )

            today = start_datetime.date()

            start_datetime = timezone.make_aware(

                datetime.combine(
                    today,
                    slot.start_time,
                )

            )

            end_datetime = timezone.make_aware(

                datetime.combine(
                    today,
                    slot.end_time,
                )

            )

        else:

            if start_datetime is None:

                raise ValueError(
                    "زمان شروع الزامی است."
                )

            if end_datetime is None:

                raise ValueError(
                    "زمان پایان الزامی است."
                )


        # -----------------------------
        # کنترل فعال بودن
        # -----------------------------

        ReservationService.validate_active_objects(
            facility=facility,
            residence=residence,
        )

        # -----------------------------
        # کنترل مدت رزرو
        # -----------------------------

        ReservationService.validate_duration(
            facility=facility,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        )

        # -----------------------------
        # کنترل ساعت کاری
        # -----------------------------

        ReservationService.validate_working_hours(
            facility=facility,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        )

        # -----------------------------
        # کنترل قوانین رزرو
        # -----------------------------

        ReservationService.validate_reservation_policy(
            facility=facility,
            residence=residence,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            guest_count=guest_count,
        )



        # -----------------------------
        # محاسبه مبلغ
        # -----------------------------

        (
            price_snapshot,
            deposit_snapshot,
            total_price,
        ) = ReservationService.calculate_price(
            facility=facility,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            guest_count=guest_count,
        )

        # -----------------------------
        # وضعیت اولیه رزرو
        # -----------------------------

        if facility.requires_approval:

            reservation_status = (
                Reservation.ReservationStatus.REQUESTED
            )

        else:

            reservation_status = (
                Reservation.ReservationStatus.APPROVED
            )

        # -----------------------------
        # ایجاد رزرو
        # -----------------------------

        reservation = Reservation.objects.create(

            facility=facility,

            slot=slot,

            residence=residence,

            created_by=created_by,

            start_datetime=start_datetime,

            end_datetime=end_datetime,

            guest_count=guest_count,

            notes=notes,

            reservation_status=reservation_status,

            payment_status=Reservation.PaymentStatus.UNPAID,

            price_snapshot=price_snapshot,

            deposit_snapshot=deposit_snapshot,

            total_price=total_price,

            remaining_amount=total_price,

        )

        reservation.reservation_number = (
            ReservationService.generate_reservation_number(
                reservation
            )
        )

        reservation.save(
            update_fields=[
                "reservation_number",
            ]
        )

        ReservationLog.objects.create(
            reservation=reservation,
            action=ReservationLog.Action.CREATED,
            user=created_by,
            description="رزرو ایجاد شد.",
        )

        return reservation
    
    # ==================================================
    # تایید رزرو
    # ==================================================

    @staticmethod
    @transaction.atomic
    def approve_reservation(
        *,
        reservation,
        approved_by,
        note="",
    ):

        if (
            reservation.reservation_status
            !=
            Reservation.ReservationStatus.REQUESTED
        ):

            raise ValueError(
                "این رزرو قابل تایید نیست."
            )

        reservation.reservation_status = (
            Reservation.ReservationStatus.APPROVED
        )

        reservation.approved_by = approved_by

        reservation.approved_at = timezone.now()

        reservation.admin_note = note

        reservation.save()

        ReservationLog.objects.create(
            reservation=reservation,
            action=ReservationLog.Action.ADMIN_APPROVED,
            user=approved_by,
            description="رزرو تایید شد.",
        )

        return reservation

    # ==================================================
    # رد رزرو
    # ==================================================

    @staticmethod
    @transaction.atomic
    def reject_reservation(
        *,
        reservation,
        rejected_by,
        reason="",
    ):

        if (
            reservation.reservation_status
            !=
            Reservation.ReservationStatus.REQUESTED
        ):

            raise ValueError(
                "این رزرو قابل رد نیست."
            )

        reservation.reservation_status = (
            Reservation.ReservationStatus.REJECTED
        )

        reservation.admin_note = reason

        reservation.save()

        ReservationLog.objects.create(
            reservation=reservation,
            action=ReservationLog.Action.REJECTED,
            user=rejected_by,
            description=reason,
        )

        return reservation 

    # ==================================================
    # لغو رزرو
    # ==================================================

    @staticmethod
    @transaction.atomic
    def cancel_reservation(
        *,
        reservation,
        cancelled_by,
        reason="",
    ):

        if reservation.reservation_status in [

            Reservation.ReservationStatus.CANCELLED,

            Reservation.ReservationStatus.COMPLETED,

        ]:

            raise ValueError(
                "رزرو قابل لغو نیست."
            )

        reservation.reservation_status = (
            Reservation.ReservationStatus.CANCELLED
        )

        reservation.cancelled_by = cancelled_by

        reservation.cancelled_at = timezone.now()

        reservation.cancel_reason = reason

        reservation.save()

        ReservationLog.objects.create(

            reservation=reservation,

            action=ReservationLog.Action.ADMIN_CANCELLED,

            user=cancelled_by,

            description=reason,

        )

        return reservation

    # ==================================================
    # ورود (Check In)
    # ==================================================

    @staticmethod
    @transaction.atomic
    def check_in(
        *,
        reservation,
        user,
    ):

        if (
            reservation.reservation_status
            !=
            Reservation.ReservationStatus.APPROVED
        ):

            raise ValueError(
                "فقط رزرو تایید شده قابل ورود است."
            )

        if reservation.checked_in_at:

            raise ValueError(
                "قبلاً ورود ثبت شده است."
            )

        reservation.checked_in_at = timezone.now()

        reservation.save(
            update_fields=[
                "checked_in_at",
            ]
        )

        ReservationLog.objects.create(
            reservation=reservation,
            action=ReservationLog.Action.CHECK_IN,
            user=user,
            description="ورود ثبت شد.",
        )

        return reservation

    # ==================================================
    # خروج (Check Out)
    # ==================================================

    @staticmethod
    @transaction.atomic
    def check_out(
        *,
        reservation,
        user,
    ):

        if reservation.checked_in_at is None:

            raise ValueError(
                "ابتدا باید ورود ثبت شود."
            )

        if reservation.checked_out_at:

            raise ValueError(
                "قبلاً خروج ثبت شده است."
            )

        reservation.checked_out_at = timezone.now()

        reservation.reservation_status = (
            Reservation.ReservationStatus.COMPLETED
        )

        reservation.save(
            update_fields=[
                "checked_out_at",
                "reservation_status",
            ]
        )

        ReservationLog.objects.create(
            reservation=reservation,
            action=ReservationLog.Action.CHECK_OUT,
            user=user,
            description="خروج ثبت شد.",
        )

        return reservation
    # ==================================================
    # ثبت پرداخت
    # ==================================================

    @staticmethod
    @transaction.atomic
    def register_payment(
        *,
        reservation,
        amount,
        payment_method,
        payment_type,
        created_by,
        reference_number="",
        note="",
    ):

        payment = ReservationPayment.objects.create(

            reservation=reservation,

            amount=amount,

            payment_method=payment_method,

            payment_type=payment_type,

            created_by=created_by,

            reference_number=reference_number,

            note=note,

        )

        # ------------------------------------------
        # بروزرسانی مبالغ
        # ------------------------------------------

        if payment_type == ReservationPayment.PaymentType.REFUND:

            reservation.paid_amount -= amount

            if reservation.paid_amount < 0:

                reservation.paid_amount = 0

        else:

            reservation.paid_amount += amount

        reservation.remaining_amount = max(

            reservation.total_price - reservation.paid_amount,

            0,

        )

        # ------------------------------------------
        # بروزرسانی وضعیت پرداخت
        # ------------------------------------------

        if reservation.paid_amount == 0:

            reservation.payment_status = (
                Reservation.PaymentStatus.UNPAID
            )

        elif reservation.remaining_amount == 0:

            reservation.payment_status = (
                Reservation.PaymentStatus.PAID
            )

        else:

            reservation.payment_status = (
                Reservation.PaymentStatus.PARTIAL
            )

        reservation.save(
            update_fields=[
                "paid_amount",
                "remaining_amount",
                "payment_status",
            ]
        )

        # ------------------------------------------
        # انتخاب نوع لاگ
        # ------------------------------------------

        if payment_type == ReservationPayment.PaymentType.REFUND:

            action = ReservationLog.Action.REFUND_PAYMENT

            description = (
                f"استرداد مبلغ {amount:,.0f}"
            )

        elif reservation.remaining_amount == 0:

            action = ReservationLog.Action.FULL_PAYMENT

            description = (
                f"تسویه کامل ({amount:,.0f})"
            )

        else:

            action = ReservationLog.Action.PARTIAL_PAYMENT

            description = (
                f"پرداخت مبلغ {amount:,.0f}"
            )

        ReservationLog.objects.create(

            reservation=reservation,

            action=action,

            user=created_by,

            description=description,

        )

        return payment

    # ==================================================
    # استرداد وجه
    # ==================================================

    @staticmethod
    @transaction.atomic
    def refund(
        *,
        reservation,
        amount,
        created_by,
        payment_method=ReservationPayment.PaymentMethod.CASH,
        reference_number="",
        note="",
    ):

        if amount <= 0:

            raise ValueError(
                "مبلغ استرداد باید بیشتر از صفر باشد."
            )

        if amount > reservation.paid_amount:

            raise ValueError(
                "مبلغ استرداد نمی‌تواند بیشتر از مبلغ پرداخت‌شده باشد."
            )

        return ReservationService.register_payment(

            reservation=reservation,

            amount=amount,

            payment_method=payment_method,

            payment_type=ReservationPayment.PaymentType.REFUND,

            created_by=created_by,

            reference_number=reference_number,

            note=note,

        )

    @staticmethod
    @transaction.atomic
    def expire_pending_reservations():

        expire_before = (
            timezone.now()
            - timedelta(
                hours=settings.RESERVATION_REQUEST_EXPIRE_HOURS
            )
        )

        reservations = Reservation.objects.filter(
            reservation_status=Reservation.ReservationStatus.REQUESTED,
            created_at__lte=expire_before,
        )

        for reservation in reservations:

            reservation.reservation_status = (
                Reservation.ReservationStatus.REJECTED
            )

            reservation.save(
                update_fields=[
                    "reservation_status",
                ]
            )

            ReservationLog.objects.create(
                reservation=reservation,
                action=ReservationLog.Action.EXPIRED,
                user=reservation.created_by,
                description="درخواست به صورت خودکار منقضی شد.",
            )

        return reservations.count()

    @staticmethod
    @transaction.atomic
    def auto_complete():

        complete_before = (
            timezone.now()
            - timedelta(
                hours=settings.AUTO_COMPLETE_AFTER_HOURS
            )
        )

        reservations = Reservation.objects.filter(

            reservation_status=Reservation.ReservationStatus.APPROVED,

            end_datetime__lte=complete_before,

        )

        for reservation in reservations:

            reservation.reservation_status = (
                Reservation.ReservationStatus.COMPLETED
            )

            reservation.save(
                update_fields=[
                    "reservation_status",
                ]
            )

            ReservationLog.objects.create(

                reservation=reservation,

                action=ReservationLog.Action.COMPLETED,

                user=reservation.created_by,

                description="رزرو به صورت خودکار پایان یافت.",

            )

        return reservations.count()

    @staticmethod
    def calculate_late_checkout_charge(
        reservation,
    ):

        if reservation.checked_out_at is None:

            return 0

        late = (
            reservation.checked_out_at
            - reservation.end_datetime
        )

        minutes = late.total_seconds() / 60

        if minutes <= settings.LATE_CHECKOUT_GRACE_MINUTES:

            return 0

        reservation.late_minutes = int(minutes)

        charge = reservation.price_snapshot

        reservation.extra_charge = charge

        reservation.save(
            update_fields=[
                "late_minutes",
                "extra_charge",
            ]
        )

        return charge

    @staticmethod
    def cancellation_penalty(
        reservation,
    ):

        facility = reservation.facility

        if not facility.allow_cancellation:

            return reservation.total_price

        deadline = (
            reservation.start_datetime
            - timedelta(
                hours=facility.cancellation_deadline_hours
            )
        )

        if timezone.now() <= deadline:

            return 0

        return reservation.deposit_snapshot                