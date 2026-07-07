from django.contrib import admin

from .models import (

    Visitor,

    VisitorVehicle,

    VisitorLog,

)


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):

    list_display = (

        "id",

        "full_name",

        "mobile",

        "visitor_type",

        "status",

        "valid_from",

        "valid_until",

    )

    list_filter = (

        "visitor_type",

        "status",

    )

    search_fields = (

        "full_name",

        "mobile",

        "national_code",

    )

    ordering = (

        "-created_at",

    )


@admin.register(VisitorVehicle)
class VisitorVehicleAdmin(admin.ModelAdmin):

    list_display = (

        "visitor",

        "plate_number",

        "car_model",

        "color",

    )

    search_fields = (

        "plate_number",

    )


@admin.register(VisitorLog)
class VisitorLogAdmin(admin.ModelAdmin):

    list_display = (

        "visitor",

        "action",

        "user",

        "created_at",

    )

    list_filter = (

        "action",

    )

    ordering = (

        "-created_at",

    )