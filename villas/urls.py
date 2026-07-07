from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    VillaViewSet,
    ResidenceViewSet,
)

router = DefaultRouter()

router.register(
    r"villas",
    VillaViewSet,
    basename="villa",
)

router.register(
    r"residences",
    ResidenceViewSet,
    basename="residence",
)

urlpatterns = [
    path(
        "",
        include(router.urls),
    ),
]