from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import GateViewSet

router = DefaultRouter()

router.register(
    "",
    GateViewSet,
    basename="gate",
)

urlpatterns = [

    path(
        "",
        include(router.urls),
    ),

]
