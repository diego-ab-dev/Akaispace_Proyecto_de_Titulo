from django.apps import AppConfig


class AppprincipalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'appPrincipal'

    def ready(self):
        from appPrincipal import recomendaciones  # noqa: F401  conecta las señales del recálculo (HU-07)
