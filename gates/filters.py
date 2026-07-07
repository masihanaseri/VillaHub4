from django.db.models import Q

from rest_framework.filters import BaseFilterBackend


class GateFilterBackend(BaseFilterBackend):
    """
    فیلتر سفارشی برای Gate بدون وابستگی به django-filter.

    Query params پشتیبانی شده:
        - is_active: "true" / "false"
        - has_coordinates: "true" / "false"
        - search: جستجو در نام و کد درب
    """

    def filter_queryset(
        self,
        request,
        queryset,
        view,
    ):

        params = request.query_params

        is_active = params.get("is_active")

        if is_active is not None:

            queryset = queryset.filter(
                is_active=self._to_bool(is_active),
            )

        has_coordinates = params.get("has_coordinates")

        if has_coordinates is not None:

            if self._to_bool(has_coordinates):

                queryset = queryset.exclude(
                    latitude__isnull=True,
                ).exclude(
                    longitude__isnull=True,
                )

            else:

                queryset = queryset.filter(
                    Q(latitude__isnull=True) | Q(longitude__isnull=True),
                )

        search = params.get("search")

        if search:

            queryset = queryset.filter(
                Q(name__icontains=search) | Q(code__icontains=search),
            )

        return queryset

    @staticmethod
    def _to_bool(raw_value):

        return str(raw_value).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
