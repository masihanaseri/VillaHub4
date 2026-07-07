from django.contrib import admin

from .models import (
    Reservation,
    ReservationSlot,
    ReservationLog,
    ReservationPayment,
)


@admin.register(ReservationSlot)
class ReservationSlotAdmin(admin.ModelAdmin):
    """
    مدیریت سانس‌های قابل رزرو امکانات
    """

    list_display = (
        "facility",
        "title",
        "start_time",
        "end_time",
        "capacity",
        "is_active",
        "sort_order",
    )

    list_filter = (
        "facility__township",
        "facility",
        "is_active",
    )

    search_fields = (
        "title",
        "facility__name",
        "facility__code",
    )

    ordering = (
        "facility",
        "sort_order",
        "start_time",
    )

    readonly_fields = (
        "uuid",
        "created_at",
        "updated_at",
    )


class ReservationPaymentInline(admin.TabularInline):

    model = ReservationPayment

    extra = 0

    readonly_fields = (
        "uuid",
        "created_at",
    )

    fields = (
        "amount",
        "payment_method",
        "payment_type",
        "reference_number",
        "created_by",
        "note",
        "created_at",
    )


class ReservationLogInline(admin.TabularInline):

    model = ReservationLog

    extra = 0

    readonly_fields = (
        "action",
        "user",
        "description",
        "created_at",
    )

    fields = readonly_fields

    def has_add_permission(self, request, obj=None):

        return False

    def has_change_permission(self, request, obj=None):

        return False

    def has_delete_permission(self, request, obj=None):

        return False


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """
    مدیریت رزروها
    """

    list_display = (
        "reservation_number",
        "facility",
        "residence",
        "created_by",
        "start_datetime",
        "end_datetime",
        "reservation_status",
        "payment_status",
    )

    list_filter = (
        "reservation_status",
        "payment_status",
        "facility__township",
        "facility",
    )

    search_fields = (
        "reservation_number",
        "facility__name",
        "residence__villa__code",
        "created_by__username",
    )

    autocomplete_fields = (
        "facility",
        "residence",
        "created_by",
        "approved_by",
    )

    readonly_fields = (
        "uuid",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-start_datetime",
    )

    inlines = (
        ReservationPaymentInline,
        ReservationLogInline,
    )

    fieldsets = (

        (
            "اطلاعات رزرو",
            {
                "fields": (
                    "reservation_number",
                    "facility",
                    "slot",
                    "residence",
                    "created_by",
                    "start_datetime",
                    "end_datetime",
                    "guest_count",
                )
            },
        ),

        (
            "وضعیت",
            {
                "fields": (
                    "reservation_status",
                    "payment_status",
                )
            },
        ),

        (
            "مالی",
            {
                "fields": (
                    "price_snapshot",
                    "deposit_snapshot",
                    "total_price",
                    "paid_amount",
                    "remaining_amount",
                    "extra_charge",
                )
            },
        ),

        (
            "تأیید مدیر",
            {
                "fields": (
                    "approved_by",
                    "approved_at",
                )
            },
        ),

        (
            "لغو، ورود و خروج",
            {
                "fields": (
                    "cancelled_by",
                    "cancelled_at",
                    "checked_in_at",
                    "checked_out_at",
                    "late_minutes",
                )
            },
        ),

        (
            "توضیحات",
            {
                "fields": (
                    "cancel_reason",
                    "admin_note",
                    "notes",
                )
            },
        ),

        (
            "اطلاعات سیستمی",
            {
                "fields": (
                    "uuid",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
