from django.shortcuts import get_object_or_404

from rest_framework import viewsets

from rest_framework.decorators import action

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from gates.models import Gate

from .filters import GuardFilterBackend

from .models import Guard

from .permissions import (
    HasActiveTownship,
    IsGuardOfActiveTownship,
)

from .serializers import GuardSerializer

from .services import GuardService


class GuardViewSet(viewsets.ModelViewSet):
    """
    مطابق الگوی ReservationViewSet/VisitorViewSet: دسترسی بر اساس عضویت در
    شهرک فعال کنترل می‌شود. در صورت نیاز به محدودیت نقش/مجوز دقیق‌تر روی
    عملیات نوشتن، می‌توان CanManageGuards را از permissions.py به لیست زیر
    اضافه کرد (نیازمند ثبت Permission با کد 'guards.manage' برای نقش‌های
    مربوطه در accounts).
    """

    serializer_class = GuardSerializer

    permission_classes = [
        IsAuthenticated,
        HasActiveTownship,
        IsGuardOfActiveTownship,
    ]

    filter_backends = [
        GuardFilterBackend,
    ]

    def get_queryset(self):

        township = self.request.user.active_township

        if township is None:

            return Guard.objects.none()

        return (
            Guard.objects.filter(
                township=township,
            )
            .select_related(
                "township",
                "user",
            )
            .prefetch_related(
                "gates",
                "shifts",
                "logs",
            )
            .order_by(
                "employee_code",
            )
        )

    def get_serializer_context(self):

        context = super().get_serializer_context()

        context["township"] = (
            self.request.user.active_township
        )

        return context

    # ==================================================
    # شیفت حضور
    # ==================================================

    @action(
        detail=True,
        methods=["post"],
    )
    def start_shift(self, request, pk=None):

        guard = self.get_object()

        GuardService.start_shift(
            guard=guard,
            performed_by=request.user,
        )

        guard.refresh_from_db()

        return Response(
            self.get_serializer(guard).data,
        )

    @action(
        detail=True,
        methods=["post"],
    )
    def end_shift(self, request, pk=None):

        guard = self.get_object()

        GuardService.end_shift(
            guard=guard,
            performed_by=request.user,
        )

        guard.refresh_from_db()

        return Response(
            self.get_serializer(guard).data,
        )

    # ==================================================
    # فعال‌سازی / غیرفعال‌سازی
    # ==================================================

    @action(
        detail=True,
        methods=["post"],
    )
    def activate(self, request, pk=None):

        guard = self.get_object()

        GuardService.activate(
            guard=guard,
            performed_by=request.user,
        )

        guard.refresh_from_db()

        return Response(
            self.get_serializer(guard).data,
        )

    @action(
        detail=True,
        methods=["post"],
    )
    def deactivate(self, request, pk=None):

        guard = self.get_object()

        GuardService.deactivate(
            guard=guard,
            performed_by=request.user,
        )

        guard.refresh_from_db()

        return Response(
            self.get_serializer(guard).data,
        )

    # ==================================================
    # تخصیص / حذف درب
    # ==================================================

    @action(
        detail=True,
        methods=["post"],
    )
    def assign_gate(self, request, pk=None):

        guard = self.get_object()

        gate_id = request.data.get("gate_id")

        if not gate_id:

            return Response(
                {"gate_id": ["شناسه درب الزامی است."]},
                status=400,
            )

        gate = get_object_or_404(
            Gate,
            pk=gate_id,
        )

        GuardService.assign_gate(
            guard=guard,
            gate=gate,
            performed_by=request.user,
        )

        guard.refresh_from_db()

        return Response(
            self.get_serializer(guard).data,
        )

    @action(
        detail=True,
        methods=["post"],
    )
    def remove_gate(self, request, pk=None):

        guard = self.get_object()

        gate_id = request.data.get("gate_id")

        if not gate_id:

            return Response(
                {"gate_id": ["شناسه درب الزامی است."]},
                status=400,
            )

        gate = get_object_or_404(
            Gate,
            pk=gate_id,
        )

        GuardService.remove_gate(
            guard=guard,
            gate=gate,
            performed_by=request.user,
        )

        guard.refresh_from_db()

        return Response(
            self.get_serializer(guard).data,
        )

    # ==================================================
    # لیست‌های کمکی
    # ==================================================

    @action(
        detail=False,
        methods=["get"],
    )
    def active(self, request):

        queryset = self.filter_queryset(
            self.get_queryset(),
        ).filter(
            is_active=True,
        )

        return Response(
            self.get_serializer(queryset, many=True).data,
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def on_shift(self, request):

        queryset = self.filter_queryset(
            self.get_queryset(),
        ).filter(
            shifts__ended_at__isnull=True,
        ).distinct()

        return Response(
            self.get_serializer(queryset, many=True).data,
        )
