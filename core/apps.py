from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self) -> None:
        # Registra os signals (ex.: limpeza de arquivos orfaos de Requisicoes).
        from . import signals  # noqa: F401
