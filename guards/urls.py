from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import GuardViewSet

router = DefaultRouter()

router.register(
    "",
    GuardViewSet,
    basename="guard",
)

urlpatterns = [

    path(
        "",
        include(router.urls),
    ),

]
