from django.apps import AppConfig


class BillingConfig(AppConfig):
    """
    App configuration for the Billing module.

    This module is self-contained: it never imports models from other
    apps at module load time. All cross-app references use lazy string
    FKs ("app_label.Model") and the notification bridge in services.py
    resolves the Notifications app dynamically, so the Billing app can
    be dropped into VillaHub without touching existing apps.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "billing"
    verbose_name = "Billing"

    def ready(self):
        # Import signal handlers so they are registered on startup.
        from billing import signals  # noqa: F401
