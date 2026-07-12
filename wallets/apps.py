from django.apps import AppConfig


class WalletsConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "wallets"

    verbose_name = "Wallet Management"

    def ready(self):

        from . import signals  # noqa: F401
