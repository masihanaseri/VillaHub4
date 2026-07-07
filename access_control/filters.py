from django.db.models import Q

from rest_framework.filters import BaseFilterBackend


def _to_bool(raw_value):

    return str(raw_value).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


class AccessPassFilterBackend(BaseFilterBackend):
    """
    فیلتر سفارشی برای AccessPass.

    Query params پشتیبانی شده:
        - status: PENDING / APPROVED / REJECTED / CANCELLED /
                  CHECKED_IN / CHECKED_OUT / EXPIRED
        - gate: id درب
        - visitor: id مهمان
        - valid_from / valid_until: بازه زمانی (ISO format)
        - is_active: "true" / "false" (وضعیت‌های در جریان)
        - search: جستجو در نام و موبایل مهمان
    """

    def filter_queryset(
        self,
        request,
        queryset,
        view,
    ):

        params = request.query_params

        status = params.get("status")

        if status:

            queryset = queryset.filter(
                status=status.upper(),
            )

        gate_id = params.get("gate")

        if gate_id:

            queryset = queryset.filter(
                gate_id=gate_id,
            )

        visitor_id = params.get("visitor")

        if visitor_id:

            queryset = queryset.filter(
                visitor_id=visitor_id,
            )

        valid_from = params.get("valid_from")

        if valid_from:

            queryset = queryset.filter(
                valid_from__gte=valid_from,
            )

        valid_until = params.get("valid_until")

        if valid_until:

            queryset = queryset.filter(
                valid_until__lte=valid_until,
            )

        is_active = params.get("is_active")

        if is_active is not None:

            if _to_bool(is_active):

                queryset = queryset.filter(
                    status__in=[
                        "PENDING",
                        "APPROVED",
                        "CHECKED_IN",
                    ],
                )

            else:

                queryset = queryset.exclude(
                    status__in=[
                        "PENDING",
                        "APPROVED",
                        "CHECKED_IN",
                    ],
                )

        search = params.get("search")

        if search:

            queryset = queryset.filter(
                Q(visitor__full_name__icontains=search)
                | Q(visitor__mobile__icontains=search),
            )

        return queryset


class AccessLogFilterBackend(BaseFilterBackend):
    """
    فیلتر سفارشی برای AccessLog.

    Query params پشتیبانی شده:
        - access_pass: id کارت تردد
        - gate: id درب
        - guard: id نگهبان
        - action: CHECK_IN / CHECK_OUT / DENIED / QR_SCAN / MANUAL / MANAGER
        - today: "true" برای فقط رویدادهای امروز
        - date_from / date_to: بازه زمانی created_at (ISO format)
    """

    def filter_queryset(
        self,
        request,
        queryset,
        view,
    ):

        params = request.query_params

        access_pass_id = params.get("access_pass")

        if access_pass_id:

            queryset = queryset.filter(
                access_pass_id=access_pass_id,
            )

        gate_id = params.get("gate")

        if gate_id:

            queryset = queryset.filter(
                gate_id=gate_id,
            )

        guard_id = params.get("guard")

        if guard_id:

            queryset = queryset.filter(
                guard_id=guard_id,
            )

        action = params.get("action")

        if action:

            queryset = queryset.filter(
                action=action.upper(),
            )

        if _to_bool(params.get("today")):

            queryset = queryset.today()

        date_from = params.get("date_from")

        if date_from:

            queryset = queryset.filter(
                created_at__gte=date_from,
            )

        date_to = params.get("date_to")

        if date_to:

            queryset = queryset.filter(
                created_at__lte=date_to,
            )

        return queryset
