from django.apps import AppConfig


class RatingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ratings'
    verbose_name = 'Ratings'

    def ready(self):
        """Import signal handlers when app is ready"""
        try:
            from . import signals
        except ImportError:
            pass