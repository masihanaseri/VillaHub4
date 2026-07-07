from django.contrib import admin

from .models import (
    Guard,
    GuardLog,
    GuardShift,
)


class GuardShiftInline(admin.TabularInline):

    model = GuardShift

    extra = 0

    readonly_fields = (
        "started_at",
        "ended_at",
        "created_at",
    )

    fields = readonly_fields

    def has_add_permission(self, request, obj=None):

        return False

    def has_delete_permission(self, request, obj=None):

        return False


class GuardLogInline(admin.TabularInline):

    model = GuardLog

    extra = 0

    readonly_fields = (
        "action",
        "performed_by",
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


@admin.register(Guard)
class GuardAdmin(admin.ModelAdmin):
    """
    مدیریت نگهبانان
    """

    list_display = (
        "employee_code",
        "user",
        "township",
        "phone",
        "shift",
        "is_active",
        "hired_at",
    )

    list_filter = (
        "township",
        "shift",
        "is_active",
    )

    search_fields = (
        "employee_code",
        "phone",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__mobile",
    )

    autocomplete_fields = (
        "township",
        "user",
        "gates",
    )

    list_select_related = (
        "township",
        "user",
    )

    ordering = (
        "township",
        "employee_code",
    )

    readonly_fields = (
        "uuid",
        "created_at",
        "updated_at",
    )

    inlines = (
        GuardShiftInline,
        GuardLogInline,
    )

    fieldsets = (

        (
            "اطلاعات نگهبان",
            {
                "fields": (
                    "township",
                    "user",
                    "employee_code",
                    "phone",
                    "shift",
                    "is_active",
                    "hired_at",
                )
            },
        ),

        (
            "دربهای تحت مسئولیت",
            {
                "fields": (
                    "gates",
                )
            },
        ),

        (
            "توضیحات",
            {
                "fields": (
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

    actions = [
        "activate_guards",
        "deactivate_guards",
    ]

    @admin.action(description="فعال‌سازی نگهبانان انتخاب‌شده")
    def activate_guards(self, request, queryset):

        updated = queryset.update(is_active=True)

        self.message_user(
            request,
            f"{updated} نگهبان فعال شد.",
        )

    @admin.action(description="غیرفعال‌سازی نگهبانان انتخاب‌شده")
    def deactivate_guards(self, request, queryset):

        updated = queryset.update(is_active=False)

        self.message_user(
            request,
            f"{updated} نگهبان غیرفعال شد.",
        )


@admin.register(GuardShift)
class GuardShiftAdmin(admin.ModelAdmin):

    list_display = (
        "guard",
        "started_at",
        "ended_at",
    )

    list_filter = (
        "guard__township",
    )

    search_fields = (
        "guard__employee_code",
    )

    ordering = (
        "-started_at",
    )

    readonly_fields = (
        "uuid",
        "created_at",
        "updated_at",
    )


@admin.register(GuardLog)
class GuardLogAdmin(admin.ModelAdmin):

    list_display = (
        "guard",
        "action",
        "performed_by",
        "created_at",
    )

    list_filter = (
        "action",
        "guard__township",
    )

    search_fields = (
        "guard__employee_code",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "uuid",
        "created_at",
        "updated_at",
    )
