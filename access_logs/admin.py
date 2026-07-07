from django.contrib import admin

from .models import AccessLog


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    """
    مشاهده دفترچه تردد. عمداً امکان افزودن/ویرایش/حذف از پنل ادمین غیرفعال
    شده تا صحت تاریخچه تردد (audit trail) دستکاری نشود؛ ثبت فقط از طریق
    AccessLogService (API یا دستگاه‌های تردد) انجام می‌شود.
    """

    list_display = (
        "occurred_at",
        "township",
        "gate",
        "guard",
        "direction",
        "access_method",
        "subject_display",
    )

    list_filter = (
        "township",
        "gate",
        "direction",
        "access_method",
    )

    search_fields = (
        "plate_number",
        "visitor__full_name",
        "residence__user__username",
        "gate__code",
        "gate__name",
        "guard__employee_code",
    )

    autocomplete_fields = (
        "township",
        "gate",
        "guard",
        "visitor",
        "residence",
    )

    ordering = (
        "-occurred_at",
    )

    readonly_fields = (
        "uuid",
        "township",
        "gate",
        "guard",
        "visitor",
        "residence",
        "direction",
        "access_method",
        "plate_number",
        "occurred_at",
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

    @admin.display(description="موضوع تردد")
    def subject_display(self, obj):

        return obj.subject_display
