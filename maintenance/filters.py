import django_filters

from .models import MaintenanceRequest


class MaintenanceFilter(
    django_filters.FilterSet
):

    class Meta:

        model = MaintenanceRequest

        fields = [
            "township",
            "villa",
            "status",
            "priority",
            "category",
            "assigned_to",
        ]