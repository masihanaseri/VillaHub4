from rest_framework import viewsets

from rest_framework.decorators import action

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from .filters import GateFilterBackend

from .models import Gate

from .permissions import (
    HasActiveTownship,
    IsGateOfActiveTownship,
)

from .serializers import GateSerializer

from .services import GateService


class GateViewSet(viewsets.ModelViewSet):
    """
    مطابق الگوی ReservationViewSet/VisitorViewSet: دسترسی بر اساس عضویت در
    شهرک فعال کنترل می‌شود. در صورت نیاز به محدودیت نقش/مجوز دقیق‌تر روی
    عملیات نوشتن، می‌توان CanManageGates را از permissions.py به لیست زیر
    اضافه کرد (نیازمند ثبت Permission با کد 'gates.manage' برای نقش‌های
    مربوطه در accounts).
    """

    serializer_class = GateSerializer

    permission_classes = [
        IsAuthenticated,
        HasActiveTownship,
        IsGateOfActiveTownship,
    ]

    filter_backends = [
        GateFilterBackend,
    ]

    def get_queryset(self):

        township = self.request.user.active_township

        if township is None:

            return Gate.objects.none()

        return (
            Gate.objects.filter(
                township=township,
            )
            .select_related(
                "township",
            )
            .order_by(
                "name",
            )
        )

    def get_serializer_context(self):

        context = super().get_serializer_context()

        context["township"] = (
            self.request.user.active_township
        )

        return context

    @action(
        detail=True,
        methods=["post"],
    )
    def activate(
        self,
        request,
        pk=None,
    ):

        gate = self.get_object()

        GateService.activate(
            gate=gate,
        )

        gate.refresh_from_db()

        serializer = self.get_serializer(
            gate,
        )

        return Response(
            serializer.data,
        )

    @action(
        detail=True,
        methods=["post"],
    )
    def deactivate(
        self,
        request,
        pk=None,
    ):

        gate = self.get_object()

        GateService.deactivate(
            gate=gate,
        )

        gate.refresh_from_db()

        serializer = self.get_serializer(
            gate,
        )

        return Response(
            serializer.data,
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def active(
        self,
        request,
    ):

        queryset = self.filter_queryset(
            self.get_queryset(),
        ).filter(
            is_active=True,
        )

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response(
            serializer.data,
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def inactive(
        self,
        request,
    ):

        queryset = self.filter_queryset(
            self.get_queryset(),
        ).filter(
            is_active=False,
        )

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response(
            serializer.data,
        )
