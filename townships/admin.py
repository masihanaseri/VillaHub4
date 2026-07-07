from django.contrib import admin
from .models import Township, TownshipSetting


class TownshipSettingInline(admin.StackedInline):
    model = TownshipSetting
    can_delete = False
    verbose_name = "تنظیمات"
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(Township)
class TownshipAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("code", "name")
    ordering = ("name",)
    readonly_fields = ("uuid", "created_at", "updated_at")
    inlines = [TownshipSettingInline]

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj:
            readonly.append("code")
        return readonly


@admin.register(TownshipSetting)
class TownshipSettingAdmin(admin.ModelAdmin):
    list_display = ("township", "reservation_enabled", "online_payment_enabled", "guest_access_enabled")
    list_filter = ("reservation_enabled", "online_payment_enabled", "guest_access_enabled")
    readonly_fields = ("uuid", "created_at", "updated_at")
