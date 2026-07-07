from django.contrib import admin

from .models import Facility


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    """
    مدیریت امکانات شهرک
    """

    list_display = (
        "code",
        "name",
        "township",
        "reservation_policy",
        "booking_mode",
        "capacity",
        "reservation_unit",
        "is_paid",
        "pricing_policy",
        "requires_approval",
        "is_active",
    )

    list_filter = (
        "township",
        "reservation_policy",
        "booking_mode",
        "reservation_unit",
        "is_paid",
        "requires_approval",
        "is_active",
        "pricing_policy",
    )

    search_fields = (
        "code",
        "name",
    )

    ordering = (
        "code",
    )

    readonly_fields = (
        "uuid",
        "created_at",
        "updated_at",
    )

    fieldsets = (

        (
            "اطلاعات اصلی",
            {
                "fields": (
                    "township",
                    "code",
                    "name",
                    "description",
                    "is_active",
                    "pricing_policy",
                )
            },
        ),

        (
            "تنظیمات رزرو",
            {
                "fields": (
                    "reservation_policy",
                    "booking_mode",
                    "capacity",
                    "reservation_unit",
                    "reservation_interval",
                    "max_parallel_reservations",
                    "max_reservation_duration",
                    "minimum_guest_count",
                    "maximum_guest_count",
                    "allow_waiting_list",
                    "available_from",
                    "available_until",
                    "requires_approval",
                    "allow_cancellation",
                    "cancellation_deadline_hours",
                )
            },
        ),

        (
            "تنظیمات مالی",
            {
                "fields": (
                    "is_paid",
                    "price",
                    "deposit",
                    "minimum_charge",
                    "tax_percent",
                    "discount_percent",
                )
            },
        ),

        (
            "اطلاعات سیستمی",
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "uuid",
                    "created_at",
                    "updated_at",
                ),
            },
        ),

    )