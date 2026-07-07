from django.shortcuts import get_object_or_404

from rest_framework import (
    mixins,
    viewsets,
)

from rest_framework.decorators import action

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from gates.models import Gate

from guards.models import Guard

from .filters import (
    AccessPassFilterBackend,
    AccessLogFilterBackend,
)

from .models import (
    AccessPass,
    AccessLog,
)

from .permissions import (
    HasActiveTownship,
    IsAccessPassOfActiveTownship,
    IsAccessLogOfActiveTownship,
    CanManageAccessControl,
    IsGuardOrManager,
)

from .serializers import (
    AccessPassSerializer,
    AccessPassDetailSerializer,
    AccessLogSerializer,
)

from .services import AccessControlService


class AccessPassViewSet(
    viewsets.ModelViewSet,
):
    """
    مدیریت کامل چرخه عمر کارت‌های تردد (AccessPass).

    زنجیره کامل معماری این‌جا شروع می‌شود:

        Visitor -> AccessPass -> Gate -> Guard -> AccessLog

    تمام منطق تجاری (تایید/رد/لغو/ورود/خروج/اعتبارسنجی QR) داخل
    AccessControlService پیاده‌سازی شده و این View فقط thin است.
    """

    permission_classes = [
        IsAuthenticated,
        HasActiveTownship,
        IsAccessPassOfActiveTownship,
        CanManageAccessControl,
    ]

    filter_backends = [
        AccessPassFilterBackend,
    ]

    def get_serializer_class(self):

        if self.action == "retrieve":

            return AccessPassDetailSerializer

        return AccessPassSerializer

    def get_queryset(self):

        township = self.request.user.active_township

        if township is None:

            return AccessPass.objects.none()

        return (
            AccessPass.objects.filter(
                township=township,
            )
            .select_related(
                "visitor",
                "gate",
                "created_by",
                "approved_by",
            )
            .prefetch_related(
                "logs",
                "logs__gate",
                "logs__guard",
            )
            .order_by(
                "-created_at",
            )
        )

    def get_serializer_context(self):

        context = super().get_serializer_context()

        context["township"] = self.request.user.active_township

        return context

    def perform_destroy(self, instance):
        """
        AccessPass یک سابقه امنیتی است و حذف فیزیکی آن مجاز نیست
        (نگاه کنید به AccessPass.delete). به‌جای حذف، از اکشن cancel
        استفاده کنید.
        """

        instance.delete()

    # ==================================================
    # تایید کارت تردد
    # ==================================================

    @action(
        detail=True,
        methods=["post"],
    )
    def approve(
        self,
        request,
        pk=None,
    ):

        access_pass = self.get_object()

        access_pass = AccessControlService.approve(
            access_pass=access_pass,
            approved_by=request.user,
            note=request.data.get(
                "note",
                "",
            ),
        )

        return Response(
            self.get_serializer(access_pass).data,
        )

    # ==================================================
    # رد کارت تردد
    # ==================================================

    @action(
        detail=True,
        methods=["post"],
    )
    def reject(
        self,
        request,
        pk=None,
    ):

        access_pass = self.get_object()

        access_pass = AccessControlService.reject(
            access_pass=access_pass,
            rejected_by=request.user,
            reason=request.data.get(
                "reason",
                "",
            ),
        )

        return Response(
            self.get_serializer(access_pass).data,
        )

    # ==================================================
    # لغو کارت تردد
    # ==================================================

    @action(
        detail=True,
        methods=["post"],
    )
    def cancel(
        self,
        request,
        pk=None,
    ):

        access_pass = self.get_object()

        access_pass = AccessControlService.cancel(
            access_pass=access_pass,
            cancelled_by=request.user,
            reason=request.data.get(
                "reason",
                "",
            ),
        )

        return Response(
            self.get_serializer(access_pass).data,
        )

    # ==================================================
    # ورود (Check In) با شناسه کارت
    # ==================================================

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[
            IsAuthenticated,
            HasActiveTownship,
            IsAccessPassOfActiveTownship,
            IsGuardOrManager,
        ],
    )
    def checkin(
        self,
        request,
        pk=None,
    ):

        access_pass = self.get_object()

        gate, guard = self._resolve_gate_and_guard(
            request,
            access_pass.township,
        )

        access_pass = AccessControlService.check_in(
            access_pass=access_pass,
            gate=gate,
            guard=guard,
            device=request.data.get("device", ""),
            latitude=request.data.get("latitude"),
            longitude=request.data.get("longitude"),
            ip_address=self._client_ip(request),
            notes=request.data.get("notes", ""),
        )

        return Response(
            self.get_serializer(access_pass).data,
        )

    # ==================================================
    # خروج (Check Out) با شناسه کارت
    # ==================================================

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[
            IsAuthenticated,
            HasActiveTownship,
            IsAccessPassOfActiveTownship,
            IsGuardOrManager,
        ],
    )
    def checkout(
        self,
        request,
        pk=None,
    ):

        access_pass = self.get_object()

        gate, guard = self._resolve_gate_and_guard(
            request,
            access_pass.township,
        )

        access_pass = AccessControlService.check_out(
            access_pass=access_pass,
            gate=gate,
            guard=guard,
            device=request.data.get("device", ""),
            latitude=request.data.get("latitude"),
            longitude=request.data.get("longitude"),
            ip_address=self._client_ip(request),
            notes=request.data.get("notes", ""),
        )

        return Response(
            self.get_serializer(access_pass).data,
        )

    # ==================================================
    # اعتبارسنجی و ورود بر اساس اسکن QR (بدون نیاز به شناسه کارت)
    # ==================================================

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[
            IsAuthenticated,
            HasActiveTownship,
            IsGuardOrManager,
        ],
    )
    def validate_qr(
        self,
        request,
    ):

        township = request.user.active_township

        gate, guard = self._resolve_gate_and_guard(
            request,
            township,
        )

        access_pass = AccessControlService.validate_qr(
            qr_token=request.data.get("qr_token"),
            gate=gate,
            guard=guard,
            device=request.data.get("device", ""),
            latitude=request.data.get("latitude"),
            longitude=request.data.get("longitude"),
            ip_address=self._client_ip(request),
        )

        return Response(
            self.get_serializer(access_pass).data,
        )

    # ==================================================
    # کارت‌های امروز
    # ==================================================

    @action(
        detail=False,
        methods=["get"],
    )
    def today(
        self,
        request,
    ):

        queryset = self.filter_queryset(
            self.get_queryset(),
        ).today()

        page = self.paginate_queryset(queryset)

        serializer = self.get_serializer(
            page if page is not None else queryset,
            many=True,
        )

        if page is not None:

            return self.get_paginated_response(
                serializer.data,
            )

        return Response(
            serializer.data,
        )

    # ==================================================
    # افرادی که هم‌اکنون داخل شهرک هستند
    # ==================================================

    @action(
        detail=False,
        methods=["get"],
    )
    def inside(
        self,
        request,
    ):

        queryset = self.filter_queryset(
            self.get_queryset(),
        ).inside()

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response(
            serializer.data,
        )

    # ==================================================
    # تاریخچه تردد یک کارت
    # ==================================================

    @action(
        detail=True,
        methods=["get"],
    )
    def history(
        self,
        request,
        pk=None,
    ):

        access_pass = self.get_object()

        logs = access_pass.logs.select_related(
            "gate",
            "guard",
        ).order_by(
            "-created_at",
        )

        serializer = AccessLogSerializer(
            logs,
            many=True,
        )

        return Response(
            serializer.data,
        )

    # ==================================================
    # ابزارهای داخلی
    # ==================================================

    @staticmethod
    def _resolve_gate_and_guard(request, township):

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

        elif hasattr(request.user, "guard_profile"):

            guard = request.user.guard_profile

        return gate, guard

    @staticmethod
    def _client_ip(request):

        forwarded_for = request.META.get(
            "HTTP_X_FORWARDED_FOR",
        )

        if forwarded_for:

            return forwarded_for.split(",")[0].strip()

        return request.META.get(
            "REMOTE_ADDR",
        )


class AccessLogViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    AccessLog یک دفترچه ممیزی است: فقط قابل مشاهده است. تمام رویدادها
    منحصراً از طریق اکشن‌های AccessPassViewSet (checkin/checkout/
    validate_qr) و AccessControlService ایجاد می‌شوند.
    """

    serializer_class = AccessLogSerializer

    permission_classes = [
        IsAuthenticated,
        HasActiveTownship,
        IsAccessLogOfActiveTownship,
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
                "access_pass",
                "access_pass__visitor",
                "gate",
                "guard",
                "guard__user",
            )
            .order_by(
                "-created_at",
            )
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def today(
        self,
        request,
    ):

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
