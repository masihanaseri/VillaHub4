from django.contrib import admin

from .models import Gate


@admin.register(Gate)
class GateAdmin(admin.ModelAdmin):
    """
    مدیریت درب‌های تردد
    """

    list_display = (
        "name",
        "code",
        "township",
        "is_active",
        "latitude",
        "longitude",
        "created_at",
    )

    list_filter = (
        "township",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "township__name",
        "township__code",
    )

    autocomplete_fields = (
        "township",
    )

    ordering = (
        "township",
        "name",
    )

    readonly_fields = (
        "uuid",
        "created_at",
        "updated_at",
    )

    fieldsets = (

        (
            "اطلاعات درب",
            {
                "fields": (
                    "township",
                    "name",
                    "code",
                    "description",
                    "is_active",
                )
            },
        ),

        (
            "موقعیت جغرافیایی",
            {
                "fields": (
                    "latitude",
                    "longitude",
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

    actions = [
        "activate_gates",
        "deactivate_gates",
    ]

    @admin.action(description="فعال‌سازی درب‌های انتخاب‌شده")
    def activate_gates(self, request, queryset):

        updated = queryset.update(is_active=True)

        self.message_user(
            request,
            f"{updated} درب فعال شد.",
        )

    @admin.action(description="غیرفعال‌سازی درب‌های انتخاب‌شده")
    def deactivate_gates(self, request, queryset):

        updated = queryset.update(is_active=False)

        self.message_user(
            request,
            f"{updated} درب غیرفعال شد.",
        )
