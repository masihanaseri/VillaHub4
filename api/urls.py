from django.urls import (
    path,
    include,
)

from .views import AppConfigView

urlpatterns = [

    # -------------------------
    # App Config
    # -------------------------

    path(
        "config/",
        AppConfigView.as_view(),
        name="app-config",
    ),

    # -------------------------
    # Villas
    # -------------------------

    path(
        "",
        include("villas.urls"),
    ),

    # -------------------------
    # Facilities
    # -------------------------

    path(
        "",
        include("facilities.urls"),
    ),

]