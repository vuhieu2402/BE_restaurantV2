"""
WebSocket routing configuration for orders app.

Defines URL patterns for WebSocket connections.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/orders/$', consumers.OrderNotificationConsumer.as_asgi()),
]
