from django.apps import AppConfig


class PurchasesConfig(AppConfig):
    name = 'purchases'

    def ready(self):
        from . import signals  # noqa: F401
