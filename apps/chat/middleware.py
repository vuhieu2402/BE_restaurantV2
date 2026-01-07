"""
JWT Authentication middleware for WebSocket connections.

Validates JWT tokens passed via query parameter for WebSocket connections.
"""

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken, TokenError
from rest_framework_simplejwt.exceptions import InvalidToken

logger = logging.getLogger(__name__)
User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_key):
    """
    Get user from JWT access token.

    Args:
        token_key: JWT access token string

    Returns:
        User object if valid, None otherwise
    """
    try:
        # Validate token
        access_token = AccessToken(token_key)

        # Get user ID from token
        user_id = access_token.get('user_id')

        if not user_id:
            return None

        # Get user from database
        try:
            user = User.objects.get(id=user_id)

            # Check if user is active
            if not user.is_active:
                return None

            return user

        except User.DoesNotExist:
            return None

    except (InvalidToken, TokenError) as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error validating JWT token: {str(e)}")
        return None


class JWTAuthMiddleware(BaseMiddleware):
    """
    Middleware to authenticate WebSocket connections using JWT token.

    Token should be passed as query parameter: ?token=<access_token>

    Usage in routing:
        from channels.routing import ProtocolTypeRouter, URLRouter
        from channels.auth import AuthMiddlewareStack

        application = ProtocolTypeRouter({
            'websocket': JWTAuthMiddleware(
                URLRouter(websocket_urlpatterns)
            ),
        })
    """

    async def __call__(self, scope, receive, send):
        # Parse query string from scope
        query_string = scope.get('query_string', b'').decode('utf-8')
        query_params = parse_qs(query_string)

        # Get token from query params
        token = query_params.get('token', [None])[0]

        if token:
            # Get user from token
            user = await get_user_from_token(token)

            if user:
                # Set user in scope for consumers to access
                scope['user'] = user
            else:
                # Invalid token - set as anonymous
                scope['user'] = None
        else:
            # No token provided - set as anonymous
            scope['user'] = None

        # Continue with the inner application
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """
    Shortcut function for applying JWT auth middleware.

    Usage:
        from apps.chat.middleware import JWTAuthMiddlewareStack

        application = ProtocolTypeRouter({
            'websocket': JWTAuthMiddlewareStack(
                URLRouter(websocket_urlpatterns)
            ),
        })
    """
    return JWTAuthMiddleware(inner)
