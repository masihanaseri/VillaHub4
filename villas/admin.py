from django.contrib import admin

from .models import Villa, Residence


@admin.register(Villa)
class VillaAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "name",
        "township",
        "area",
        "is_active",
    )

    list_filter = (
        "township",
        "is_active",
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


@admin.register(Residence)
class ResidenceAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "villa",
        "resident_type",
        "family_count",
        "start_date",
        "end_date",
        "is_active",
    )

    list_filter = (
        "resident_type",
        "is_active",
        "villa__township",
    )

    search_fields = (
        "user__username",
        "user__mobile",
        "villa__code",
    )

    autocomplete_fields = (
        "user",
        "villa",
    )

    list_select_related = (
        "user",
        "villa",
    )

    readonly_fields = (
        "uuid",
        "created_at",
        "updated_at",
    )