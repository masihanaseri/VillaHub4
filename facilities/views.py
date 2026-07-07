from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Facility
from .serializers import FacilitySerializer


class FacilityViewSet(viewsets.ModelViewSet):
    """
    مدیریت امکانات شهرک
    """

    serializer_class = FacilitySerializer

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        township = self.request.user.active_township

        if township is None:

            return Facility.objects.none()

        return (
            Facility.objects.filter(
                township=township,
            )
            .order_by(
                "code",
            )
        )

    def get_serializer_context(self):

        context = super().get_serializer_context()

        context["township"] = self.request.user.active_township

        return context

    def perform_create(self, serializer):

        serializer.save()

    def perform_update(self, serializer):

        serializer.save()