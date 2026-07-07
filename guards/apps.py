from django.apps import AppConfig


class GuardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "guards"
    verbose_name = "نگهبانان"

    def ready(self):
        from . import signals  # noqa: F401
