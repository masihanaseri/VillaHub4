from django.db.models import Q

from rest_framework.filters import BaseFilterBackend


class GuardFilterBackend(BaseFilterBackend):
    """
    فیلتر سفارشی برای Guard بدون وابستگی به django-filter.

    Query params پشتیبانی شده:
        - is_active: "true" / "false"
        - shift: MORNING / EVENING / NIGHT
        - on_shift: "true" / "false" (شیفت باز دارد یا نه)
        - gate: id درب
        - search: جستجو در کد پرسنلی، تلفن، نام و نام‌خانوادگی
    """

    def filter_queryset(self, request, queryset, view):

        params = request.query_params

        is_active = params.get("is_active")

        if is_active is not None:

            queryset = queryset.filter(
                is_active=self._to_bool(is_active),
            )

        shift = params.get("shift")

        if shift:

            queryset = queryset.filter(
                shift=shift.upper(),
            )

        on_shift = params.get("on_shift")

        if on_shift is not None:

            if self._to_bool(on_shift):

                queryset = queryset.filter(
                    shifts__ended_at__isnull=True,
                ).distinct()

            else:

                queryset = queryset.exclude(
                    shifts__ended_at__isnull=True,
                )

        gate_id = params.get("gate")

        if gate_id:

            queryset = queryset.filter(
                gates__id=gate_id,
            )

        search = params.get("search")

        if search:

            queryset = queryset.filter(
                Q(employee_code__icontains=search)
                | Q(phone__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__username__icontains=search),
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
