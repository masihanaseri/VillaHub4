from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import MaintenanceFilter
from .models import (
    MaintenanceComment,
    MaintenanceHistory,
    MaintenanceRequest,
)
from .permissions import (
    CanCreateMaintenance,
    CanEditMaintenance,
)
from .serializers import (
    MaintenanceCommentSerializer,
    MaintenanceRequestSerializer,
)
from .services import MaintenanceService


class MaintenanceRequestViewSet(
    viewsets.ModelViewSet,
):

    serializer_class = MaintenanceRequestSerializer

    queryset = (
        MaintenanceRequest.objects
        .select_related(
            "township",
            "villa",
            "created_by",
            "assigned_to",
        )
        .prefetch_related(
            "attachments",
            "comments",
            "history",
        )
    )

    permission_classes = [
        IsAuthenticated,
    ]

    filter_backends = [
        DjangoFilterBackend,
    ]

    filterset_class = MaintenanceFilter

    search_fields = [
        "title",
        "description",
    ]

    ordering = [
        "-created_at",
    ]

    def get_permissions(self):

        if self.action == "create":
            return [
                CanCreateMaintenance(),
            ]

        if self.action in [
            "assign",
            "change_status",
        ]:
            return [
                CanEditMaintenance(),
            ]

        return [
            IsAuthenticated(),
        ]

    def perform_create(
        self,
        serializer,
    ):

        maintenance = serializer.save(
            created_by=self.request.user,
        )

        MaintenanceHistory.objects.create(
            maintenance=maintenance,
            user=self.request.user,
            old_status="",
            new_status=maintenance.status,
            note="درخواست ثبت شد",
        )

    @action(
        detail=True,
        methods=["post"],
    )
    def assign(
        self,
        request,
        pk=None,
    ):

        maintenance = self.get_object()

        maintenance.assigned_to_id = request.data.get(
            "assigned_to",
        )

        maintenance.status = (
            MaintenanceRequest.Status.ASSIGNED
        )

        maintenance.assigned_at = timezone.now()

        maintenance.save()

        MaintenanceHistory.objects.create(
            maintenance=maintenance,
            user=request.user,
            old_status=MaintenanceRequest.Status.OPEN,
            new_status=MaintenanceRequest.Status.ASSIGNED,
            note="درخواست به نگهبان/مسئول اختصاص داده شد",
        )

        from .tasks import notify_assigned_maintenance

        notify_assigned_maintenance.delay(
            maintenance.id,
        )

        return Response(
            MaintenanceRequestSerializer(
                maintenance,
            ).data
        )

    @action(
        detail=True,
        methods=["post"],
    )
    def change_status(
        self,
        request,
        pk=None,
    ):

        maintenance = self.get_object()

        old_status = maintenance.status

        MaintenanceService.change_status(
            maintenance=maintenance,
            user=request.user,
            new_status=request.data.get(
                "status",
            ),
            note=request.data.get(
                "note",
                "",
            ),
        )

        if (
            maintenance.status
            == MaintenanceRequest.Status.IN_PROGRESS
            and not maintenance.started_at
        ):
            maintenance.started_at = timezone.now()

        if (
            maintenance.status
            == MaintenanceRequest.Status.DONE
        ):
            maintenance.completed_at = timezone.now()

        if (
            maintenance.status
            == MaintenanceRequest.Status.CLOSED
        ):
            maintenance.closed_at = timezone.now()

        maintenance.save()

        MaintenanceHistory.objects.create(
            maintenance=maintenance,
            user=request.user,
            old_status=old_status,
            new_status=maintenance.status,
            note=request.data.get(
                "note",
                "",
            ),
        )

        return Response(
            MaintenanceRequestSerializer(
                maintenance,
            ).data
        )

    @action(
        detail=True,
        methods=["post"],
    )
    def add_comment(
        self,
        request,
        pk=None,
    ):

        maintenance = self.get_object()

        comment = MaintenanceComment.objects.create(
            maintenance=maintenance,
            user=request.user,
            message=request.data.get(
                "message",
            ),
        )

        return Response(
            MaintenanceCommentSerializer(
                comment,
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def my_requests(
        self,
        request,
    ):

        queryset = self.get_queryset().filter(
            created_by=request.user,
        )

        return Response(
            MaintenanceRequestSerializer(
                queryset,
                many=True,
            ).data
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def assigned_to_me(
        self,
        request,
    ):

        queryset = self.get_queryset().filter(
            assigned_to=request.user,
        )

        return Response(
            MaintenanceRequestSerializer(
                queryset,
                many=True,
            ).data
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def dashboard(
        self,
        request,
    ):

        queryset = self.get_queryset()

        return Response(
            {
                "total": queryset.count(),
                "open": queryset.filter(
                    status=MaintenanceRequest.Status.OPEN,
                ).count(),
                "assigned": queryset.filter(
                    status=MaintenanceRequest.Status.ASSIGNED,
                ).count(),
                "in_progress": queryset.filter(
                    status=MaintenanceRequest.Status.IN_PROGRESS,
                ).count(),
                "done": queryset.filter(
                    status=MaintenanceRequest.Status.DONE,
                ).count(),
                "closed": queryset.filter(
                    status=MaintenanceRequest.Status.CLOSED,
                ).count(),
            }
        )