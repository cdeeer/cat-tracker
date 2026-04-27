from django.apps import AppConfig


class OggieConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Oggie'

    def ready(self):
        from . import signals  # noqa: F401
