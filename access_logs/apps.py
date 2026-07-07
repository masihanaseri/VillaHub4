from django.apps import AppConfig


class AccessLogsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "access_logs"
    verbose_name = "تردد‌های ثبت‌شده"

    def ready(self):
        from . import signals  # noqa: F401
