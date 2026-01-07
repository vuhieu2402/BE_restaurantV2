"""
Rate Limiting for Chatbot API

This module provides custom throttling classes for chatbot endpoints
to prevent abuse and ensure fair usage.
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class ChatbotBurstRateThrottle(UserRateThrottle):
    """
    Burst rate throttle for chatbot messages.

    Limits short-term bursts of messages (e.g., 10 messages per minute).
    """
    scope = 'chatbot_burst'
    rate = '10/min'  # 10 messages per minute

    def get_cache_key(self, request, view):
        """
        Generate cache key for throttling.

        Uses user ID for authenticated users.
        """
        if request.user and request.user.is_authenticated:
            ident = request.user.id
        else:
            # Use IP address for anonymous users
            ident = self.get_ident(request)

        return f'{self.scope}_{ident}'


class ChatbotSustainedRateThrottle(UserRateThrottle):
    """
    Sustained rate throttle for chatbot messages.

    Limits long-term usage (e.g., 100 messages per hour).
    """
    scope = 'chatbot_sustained'
    rate = '100/hour'  # 100 messages per hour

    def get_cache_key(self, request, view):
        """
        Generate cache key for throttling.

        Uses user ID for authenticated users.
        """
        if request.user and request.user.is_authenticated:
            ident = request.user.id
        else:
            ident = self.get_ident(request)

        return f'{self.scope}_{ident}'


class ChatbotFeedbackThrottle(UserRateThrottle):
    """
    Rate throttle for feedback submission.

    Prevents spam feedback (e.g., 5 per minute).
    """
    scope = 'chatbot_feedback'
    rate = '5/min'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.id
        else:
            ident = self.get_ident(request)

        return f'{self.scope}_{ident}'


class PerRoomRateThrottle(UserRateThrottle):
    """
    Per-room rate throttle.

    Limits messages per chat room (e.g., 20 per minute).
    This prevents spam in individual conversations.
    """
    scope = 'chatbot_room'
    rate = '20/min'

    def get_cache_key(self, request, view):
        """
        Generate cache key including room ID.

        For the message endpoint, extract room_id from kwargs.
        """
        if request.user and request.user.is_authenticated:
            user_id = request.user.id

            # Try to get room_id from URL kwargs
            room_id = view.kwargs.get('room_id')

            if room_id:
                return f'{self.scope}_{user_id}_{room_id}'
            else:
                return f'{self.scope}_{user_id}'

        return None


class StaffBypassThrottle(UserRateThrottle):
    """
    Throttle class that bypasses rate limiting for staff users.

    Staff users (managers, admins) are not rate limited.
    """
    scope = 'chatbot_staff'

    def allow_request(self, request, view):
        """
        Allow request if user is staff, otherwise use normal throttling.
        """
        if request.user and request.user.is_authenticated:
            # Check if user is staff
            if hasattr(request.user, 'user_type') and request.user.user_type in ['manager', 'admin']:
                return True

        # Fall through to normal rate limiting
        return super().allow_request(request, view)
