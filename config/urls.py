from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from wallets.callback_views import (
    payment_success_page,
    payment_failed_page,
)

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from accounts.views import (
    LoginView,
    SignupView,
    SetActiveTownshipView,
    CreateInvitationView,
    AcceptInviteView,
)

urlpatterns = [

    # =====================================================
    # Admin
    # =====================================================

    path(
        "admin/",
        admin.site.urls,
    ),

    # =====================================================
    # API Documentation
    # =====================================================

    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),

    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
        ),
        name="swagger-ui",
    ),

    # =====================================================
    # Authentication
    # =====================================================

    path(
        "api/auth/login/",
        LoginView.as_view(),
        name="login",
    ),

    path(
        "api/auth/signup/",
        SignupView.as_view(),
        name="signup",
    ),

    path(
        "api/auth/set-township/",
        SetActiveTownshipView.as_view(),
        name="set-township",
    ),

    path(
        "api/auth/invite/create/",
        CreateInvitationView.as_view(),
        name="create-invitation",
    ),

    path(
        "api/auth/invite/<uuid:token>/accept/",
        AcceptInviteView.as_view(),
        name="accept-invite",
    ),

    # =====================================================
    # JWT
    # =====================================================

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

    # =====================================================
    # Main API
    # =====================================================

    path(
        "api/",
        include("api.urls"),
    ),

    path(
        "api/dashboard/",
        include("dashboard.urls"),
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
        include("chat.urls"),
    ),

    path(
        "api/wallets/",
        include("wallets.urls"),
    ),

    path(
        "api/billing/",
        include("billing.urls"),
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

    path("payment/success/", payment_success_page, name="payment-success"),
    path("payment/failed/", payment_failed_page, name="payment-failed"),
]

# =====================================================
# Media
# =====================================================

if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )