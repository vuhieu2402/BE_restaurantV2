"""
WebSocket routing configuration for chat app.

Defines URL patterns for WebSocket connections.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/chat/(?P<room_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'^ws/presence/$', consumers.OnlinePresenceConsumer.as_asgi()),
]
