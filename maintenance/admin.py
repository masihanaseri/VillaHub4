from django.contrib import admin

from .models import (
    MaintenanceRequest,
    MaintenanceAttachment,
    MaintenanceComment,
    MaintenanceHistory,
)


class MaintenanceAttachmentInline(admin.TabularInline):
    model = MaintenanceAttachment
    extra = 0


class MaintenanceCommentInline(admin.TabularInline):
    model = MaintenanceComment
    extra = 0


class MaintenanceHistoryInline(admin.TabularInline):
    model = MaintenanceHistory
    extra = 0
    readonly_fields = (
        "user",
        "old_status",
        "new_status",
        "note",
        "created_at",
    )
    can_delete = False


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "township",
        "villa",
        "category",
        "priority",
        "status",
        "assigned_to",
        "created_at",
    )

    list_filter = (
        "township",
        "category",
        "priority",
        "status",
    )

    search_fields = (
        "title",
        "description",
    )

    autocomplete_fields = (
        "township",
        "villa",
        "created_by",
        "assigned_to",
    )

    readonly_fields = (
        "uuid",
        "created_at",
        "updated_at",
    )

    inlines = [
        MaintenanceAttachmentInline,
        MaintenanceCommentInline,
        MaintenanceHistoryInline,
    ]


@admin.register(MaintenanceAttachment)
class MaintenanceAttachmentAdmin(admin.ModelAdmin):

    list_display = (
        "maintenance",
        "uploaded_by",
        "created_at",
    )

    autocomplete_fields = (
        "maintenance",
        "uploaded_by",
    )


@admin.register(MaintenanceComment)
class MaintenanceCommentAdmin(admin.ModelAdmin):

    list_display = (
        "maintenance",
        "user",
        "created_at",
    )

    autocomplete_fields = (
        "maintenance",
        "user",
    )


@admin.register(MaintenanceHistory)
class MaintenanceHistoryAdmin(admin.ModelAdmin):

    list_display = (
        "maintenance",
        "user",
        "old_status",
        "new_status",
        "created_at",
    )

    autocomplete_fields = (
        "maintenance",
        "user",
    )

    readonly_fields = (
        "uuid",
        "created_at",
        "updated_at",
    )