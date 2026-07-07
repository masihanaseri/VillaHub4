from django.shortcuts import get_object_or_404

from rest_framework import mixins, viewsets

from rest_framework.decorators import action

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from gates.models import Gate

from guards.models import Guard

from villas.models import Residence

from visitors.models import Visitor

from .filters import AccessLogFilterBackend

from .models import AccessLog

from .permissions import (
    HasActiveTownship,
    IsAccessLogOfActiveTownship,
    ReadOnlyOrCreateOnly,
)

from .serializers import AccessLogSerializer

from .services import AccessLogService


class AccessLogViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    AccessLog یک دفترچه ممیزی است: عمداً از ModelViewSet کامل استفاده
    نشده—فقط list/retrieve/create در دسترس است. هیچ عملیات update/destroy
    (حتی برای مدیر شهرک) وجود ندارد.
    """

    serializer_class = AccessLogSerializer

    permission_classes = [
        IsAuthenticated,
        HasActiveTownship,
        IsAccessLogOfActiveTownship,
        ReadOnlyOrCreateOnly,
    ]

    filter_backends = [
        AccessLogFilterBackend,
    ]

    def get_queryset(self):

        township = self.request.user.active_township

        if township is None:

            return AccessLog.objects.none()

        return (
            AccessLog.objects.filter(
                township=township,
            )
            .select_related(
                "gate",
                "guard",
                "guard__user",
                "visitor",
                "residence",
                "residence__user",
            )
            .order_by(
                "-occurred_at",
            )
        )

    def get_serializer_context(self):

        context = super().get_serializer_context()

        context["township"] = self.request.user.active_township

        return context

    def perform_create(self, serializer):

        serializer.save()

    # ==================================================
    # Actions کمکی برای ثبت سریع ورود/خروج
    # ==================================================

    def _resolve_related(self, request, township):

        gate_id = request.data.get("gate")

        gate = get_object_or_404(
            Gate,
            pk=gate_id,
            township=township,
        )

        guard = None

        guard_id = request.data.get("guard")

        if guard_id:

            guard = get_object_or_404(
                Guard,
                pk=guard_id,
                township=township,
            )

        visitor = None

        visitor_id = request.data.get("visitor")

        if visitor_id:

            visitor = get_object_or_404(
                Visitor,
                pk=visitor_id,
                township=township,
            )

        residence = None

        residence_id = request.data.get("residence")

        if residence_id:

            residence = get_object_or_404(
                Residence,
                pk=residence_id,
                villa__township=township,
            )

        return gate, guard, visitor, residence

    @action(
        detail=False,
        methods=["post"],
    )
    def entry(self, request):

        township = request.user.active_township

        gate, guard, visitor, residence = self._resolve_related(
            request,
            township,
        )

        access_log = AccessLogService.record_entry(
            gate=gate,
            guard=guard,
            visitor=visitor,
            residence=residence,
            access_method=request.data.get(
                "access_method",
                AccessLog.AccessMethod.MANUAL,
            ),
            plate_number=request.data.get("plate_number", ""),
            notes=request.data.get("notes", ""),
        )

        return Response(
            self.get_serializer(access_log).data,
            status=201,
        )

    @action(
        detail=False,
        methods=["post"],
    )
    def exit(self, request):

        township = request.user.active_township

        gate, guard, visitor, residence = self._resolve_related(
            request,
            township,
        )

        access_log = AccessLogService.record_exit(
            gate=gate,
            guard=guard,
            visitor=visitor,
            residence=residence,
            access_method=request.data.get(
                "access_method",
                AccessLog.AccessMethod.MANUAL,
            ),
            plate_number=request.data.get("plate_number", ""),
            notes=request.data.get("notes", ""),
        )

        return Response(
            self.get_serializer(access_log).data,
            status=201,
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def today(self, request):

        queryset = self.filter_queryset(
            self.get_queryset(),
        ).today()

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response(
            serializer.data,
        )
