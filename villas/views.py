from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Villa, Residence
from .serializers import (
    VillaSerializer,
    ResidenceSerializer,
)


class VillaViewSet(viewsets.ModelViewSet):
    """
    مدیریت ویلاها
    """

    serializer_class = VillaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        township = self.request.user.active_township

        if township is None:
            return Villa.objects.none()

        return Villa.objects.filter(
            township=township
        ).order_by("code")

    def get_serializer_context(self):

        context = super().get_serializer_context()

        context["township"] = self.request.user.active_township

        return context

    def perform_create(self, serializer):

        serializer.save()

    def perform_update(self, serializer):

        serializer.save()


class ResidenceViewSet(viewsets.ModelViewSet):
    """
    مدیریت سکونت‌ها
    """

    serializer_class = ResidenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        township = self.request.user.active_township

        if township is None:
            return Residence.objects.none()

        return Residence.objects.filter(
            villa__township=township
        ).select_related(
            "villa",
            "user",
        ).order_by(
            "villa__code",
            "-start_date",
        )

    def get_serializer_context(self):

        context = super().get_serializer_context()

        context["township"] = self.request.user.active_township

        return context

    def perform_create(self, serializer):

        serializer.save()

    def perform_update(self, serializer):

        serializer.save()