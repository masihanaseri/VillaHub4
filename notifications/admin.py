from django.contrib import admin

from .models import (
    Notification,
    NotificationLog,
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):

    list_display = (

        "id",

        "title",

        "recipient",

        "notification_type",

        "priority",

        "status",

        "is_read",

        "created_at",

    )

    search_fields = (

        "title",

        "message",

        "recipient__full_name",

    )

    list_filter = (

        "notification_type",

        "priority",

        "status",

        "is_read",

    )

    ordering = (

        "-created_at",

    )


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):

    list_display = (

        "id",

        "notification",

        "channel",

        "status",

        "receiver",

        "created_at",

    )

    search_fields = (

        "receiver",

    )

    list_filter = (

        "channel",

        "status",

    )

    ordering = (

        "-created_at",

    )
