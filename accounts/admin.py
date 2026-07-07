from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, Permission, Membership, Invitation


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "mobile", "active_township", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "active_township")
    search_fields = ("username", "mobile", "first_name", "last_name")
    ordering = ("-date_joined",)

    fieldsets = BaseUserAdmin.fieldsets + (
        ("شهرک", {"fields": ("active_township",)}),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "title")
    search_fields = ("code", "title")
    filter_horizontal = ("roles",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "township", "role", "is_active")
    list_filter = ("is_active", "township", "role")
    search_fields = ("user__username", "user__mobile")
    raw_id_fields = ("user",)


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("mobile", "township", "role", "is_used", "created_at")
    list_filter = ("is_used", "township")
    search_fields = ("mobile",)
    readonly_fields = ("token", "uuid", "created_at", "updated_at")
