from rest_framework.filters import BaseFilterBackend


class AccessLogFilterBackend(BaseFilterBackend):
    """
    فیلتر سفارشی برای AccessLog.

    Query params پشتیبانی شده:
        - gate: id درب
        - guard: id نگهبان
        - visitor: id مهمان
        - residence: id سکونت
        - direction: IN / OUT
        - access_method: MANUAL / QR / PLATE / CARD
        - today: "true" برای فقط رویدادهای امروز
        - date_from / date_to: بازه زمانی occurred_at (ISO format)
    """

    def filter_queryset(self, request, queryset, view):

        params = request.query_params

        gate_id = params.get("gate")

        if gate_id:

            queryset = queryset.filter(gate_id=gate_id)

        guard_id = params.get("guard")

        if guard_id:

            queryset = queryset.filter(guard_id=guard_id)

        visitor_id = params.get("visitor")

        if visitor_id:

            queryset = queryset.filter(visitor_id=visitor_id)

        residence_id = params.get("residence")

        if residence_id:

            queryset = queryset.filter(residence_id=residence_id)

        direction = params.get("direction")

        if direction:

            queryset = queryset.filter(direction=direction.upper())

        access_method = params.get("access_method")

        if access_method:

            queryset = queryset.filter(access_method=access_method.upper())

        if str(params.get("today")).strip().lower() in ("1", "true", "yes"):

            queryset = queryset.today()

        date_from = params.get("date_from")

        if date_from:

            queryset = queryset.filter(occurred_at__gte=date_from)

        date_to = params.get("date_to")

        if date_to:

            queryset = queryset.filter(occurred_at__lte=date_to)

        return queryset
