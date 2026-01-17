from django.apps import AppConfig


class DishesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dishes'
    verbose_name = 'Dishes'

    def ready(self):
        """Import signals when app is ready"""
        import apps.dishes.signals
