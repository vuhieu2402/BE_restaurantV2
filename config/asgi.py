"""
ASGI config for restaurant project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

# Set default settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Initialize Django BEFORE importing channels
django_asgi_app = get_asgi_application()

# Import Channels after Django is initialized
from channels.routing import ProtocolTypeRouter, URLRouter

# Import chat and orders routing
from apps.chat import routing as chat_routing
from apps.orders import routing as orders_routing
from apps.chat.middleware import JWTAuthMiddlewareStack

# Combine all websocket URL patterns
websocket_urlpatterns = chat_routing.websocket_urlpatterns + orders_routing.websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': JWTAuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
