from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularSwaggerView
from accounts.views import LoginView


from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from accounts.views import (
    SetActiveTownshipView,
    SignupView,
    CreateInvitationView,
    AcceptInviteView,
)

urlpatterns = [

    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),

    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),    

    path(
        "api/token/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),

    path(
        "api/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    path(
    "api/login/",
    LoginView.as_view(),
    name="login",
    ),

    path(
        "admin/",
        admin.site.urls,
    ),

    path(
        "dashboard/",
        include("dashboard.urls"),
    ),

    path(
        "api/",
        include("api.urls"),
    ),

    path(
        "api/reservations/",
        include("reservations.urls"),
    ),

    path(
        "api/maintenance/",
        include("maintenance.urls"),
    ),

    path(

        "api/chat/",

        include(

            "chat.urls",

        ),

    ),    

    # -----------------------------
    # Accounts
    # -----------------------------

    path(
        "auth/signup/",
        SignupView.as_view(),
        name="signup",
    ),

    path(
        "auth/set-township/",
        SetActiveTownshipView.as_view(),
        name="set-township",
    ),

    path(
        "auth/invite/create/",
        CreateInvitationView.as_view(),
        name="create-invitation",
    ),

    path(
        "auth/invite/<uuid:token>/accept/",
        AcceptInviteView.as_view(),
        name="accept-invite",
    ),

    path(
        "api/notifications/",
        include("notifications.urls"),
    ),

    path(

        "api/visitors/",

        include("visitors.urls"),

    ),

    path(

        "api/gates/",

        include("gates.urls"),

    ),

    path(

        "api/guards/",

        include("guards.urls"),

    ),

    path(

        "api/access-logs/",

        include("access_logs.urls"),

    ),

    path(
        "api/access-control/",
        include("access_control.urls"),
    ),

    path(
        "api/billing/",
        include("billing.urls"),
    ),

]

if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )