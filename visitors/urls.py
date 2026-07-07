from django.urls import include
from django.urls import path

from rest_framework.routers import DefaultRouter

from .views import VisitorViewSet

router = DefaultRouter()

router.register(

    "",

    VisitorViewSet,

    basename="visitor",

)

urlpatterns = [

    path(

        "",

        include(router.urls),

    ),

]