from django.apps import AppConfig


class AccessControlConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "access_control"
    verbose_name = "کنترل تردد"

    def ready(self):
        from . import signals  # noqa: F401
