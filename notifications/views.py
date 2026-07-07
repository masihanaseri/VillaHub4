from django.utils import timezone

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(
    viewsets.ReadOnlyModelViewSet,
):

    serializer_class = NotificationSerializer

    permission_classes = [

        IsAuthenticated,

    ]

    def get_queryset(self):

        return (

            Notification.objects

            .filter(

                recipient=self.request.user,

            )

            .prefetch_related(

                "logs",

            )

            .order_by(

                "-created_at",

            )

        )
    @action(

        detail=True,

        methods=["post"],

    )
    def read(

        self,

        request,

        pk=None,

    ):

        notification = self.get_object()

        notification.is_read = True

        notification.read_at = timezone.now()

        notification.save(

            update_fields=[

                "is_read",

                "read_at",

            ]

        )

        return Response(

            {

                "success": True,

            }

        )
    @action(

        detail=False,

        methods=["post"],

    )
    def read_all(

        self,

        request,

    ):

        self.get_queryset().update(

            is_read=True,

            read_at=timezone.now(),

        )

        return Response(

            {

                "success": True,

            }

        )
    @action(

        detail=False,

        methods=["get"],

    )
    def unread(

        self,

        request,

    ):

        queryset = (

            self.get_queryset()

            .filter(

                is_read=False,

            )

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
    def unread_count(

        self,

        request,

    ):

        return Response(

            {

                "count":

                self.get_queryset()

                .filter(

                    is_read=False,

                )

                .count()

            }

        )