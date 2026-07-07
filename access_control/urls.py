from django.urls import (
    include,
    path,
)

from rest_framework.routers import DefaultRouter

from .views import (
    AccessPassViewSet,
    AccessLogViewSet,
)

router = DefaultRouter()

router.register(
    r"logs",
    AccessLogViewSet,
    basename="access-control-log",
)

router.register(
    r"",
    AccessPassViewSet,
    basename="access-pass",
)

urlpatterns = [

    path(
        "",
        include(router.urls),
    ),

]
