from django.apps import AppConfig


class VinylConfig(AppConfig):
    name = 'vinyl'

    def ready(self):
        from . import search  # noqa: F401  registra FOLD su SQLite prima della prima connessione
