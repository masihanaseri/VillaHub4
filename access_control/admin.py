from django.contrib import admin

from .models import (
    AccessPass,
    AccessLog,
)


class AccessLogInline(admin.TabularInline):
    """
    نمایش فقط-خواندنی تاریخچه تردد یک کارت، مستقیماً داخل صفحه AccessPass.
    """

    model = AccessLog

    extra = 0

    fields = (
        "action",
        "gate",
        "guard",
        "device",
        "created_at",
    )

    readonly_fields = fields

    def has_add_permission(self, request, obj=None):

        return False

    def has_change_permission(self, request, obj=None):

        return False

    def has_delete_permission(self, request, obj=None):

        return False


@admin.register(AccessPass)
class AccessPassAdmin(admin.ModelAdmin):
    """
    مدیریت کارت‌های تردد.
    """

    list_display = (
        "visitor",
        "township",
        "gate",
        "status",
        "valid_from",
        "valid_until",
        "checked_in_at",
        "checked_out_at",
    )

    list_filter = (
        "status",
        "township",
        "gate",
    )

    search_fields = (
        "visitor__full_name",
        "visitor__mobile",
        "qr_token",
        "gate__name",
        "gate__code",
    )

    autocomplete_fields = (
        "township",
        "visitor",
        "gate",
        "created_by",
        "approved_by",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "uuid",
        "qr_token",
        "approved_at",
        "checked_in_at",
        "checked_out_at",
        "created_at",
        "updated_at",
    )

    inlines = (
        AccessLogInline,
    )

    fieldsets = (

        (
            "اطلاعات کارت تردد",
            {
                "fields": (
                    "township",
                    "visitor",
                    "gate",
                    "qr_token",
                    "valid_from",
                    "valid_until",
                )
            },
        ),

        (
            "وضعیت",
            {
                "fields": (
                    "status",
                    "created_by",
                )
            },
        ),

        (
            "تایید",
            {
                "fields": (
                    "approved_by",
                    "approved_at",
                )
            },
        ),

        (
            "ورود و خروج",
            {
                "fields": (
                    "checked_in_at",
                    "checked_out_at",
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

    def has_delete_permission(self, request, obj=None):
        """
        حذف کارت تردد از پنل ادمین هم مجاز نیست (مطابق AccessPass.delete)؛
        به‌جای آن باید کارت لغو (CANCELLED) شود.
        """

        return False


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    """
    مشاهده دفترچه ممیزی کنترل تردد. عمداً افزودن/ویرایش/حذف از پنل ادمین
    غیرفعال شده تا صحت تاریخچه تردد دستکاری نشود؛ ثبت فقط از طریق
    AccessControlService انجام می‌شود.
    """

    list_display = (
        "created_at",
        "township",
        "access_pass",
        "gate",
        "guard",
        "action",
    )

    list_filter = (
        "township",
        "gate",
        "action",
    )

    search_fields = (
        "access_pass__visitor__full_name",
        "gate__name",
        "gate__code",
        "guard__employee_code",
        "device",
    )

    autocomplete_fields = (
        "township",
        "access_pass",
        "gate",
        "guard",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "uuid",
        "township",
        "access_pass",
        "gate",
        "guard",
        "action",
        "device",
        "latitude",
        "longitude",
        "ip_address",
        "notes",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):

        return False

    def has_change_permission(self, request, obj=None):

        return False

    def has_delete_permission(self, request, obj=None):

        return False
