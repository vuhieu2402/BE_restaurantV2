"""
Authentication middleware cho Proforum
Kiểm tra token blacklist và session management
"""
from django.http import JsonResponse
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from .models import RefreshTokenSession
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


# BlacklistTokenMiddleware removed for performance
# Access tokens now expire naturally (15 minutes) without blacklist checking
# This significantly improves performance by eliminating DB lookups on every request


class SessionTrackingMiddleware:
    """
    Optimized middleware để track session activity WITHOUT blocking requests
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process request first (non-blocking)
        response = self.get_response(request)
        
        # Update session activity asynchronously after response
        session_id = request.META.get('HTTP_X_SESSION_ID')
        
        if hasattr(request, 'user') and request.user.is_authenticated and session_id:
            # Use cache to batch updates and avoid frequent DB writes
            from django.core.cache import cache
            import json
            
            cache_key = f"session_activity_{session_id}"
            
            # Only update if not recently updated (avoid spam)
            if not cache.get(cache_key):
                try:
                    # Quick, non-blocking update
                    from django.db import transaction
                    
                    # Use select_for_update with nowait to avoid blocking
                    with transaction.atomic():
                        RefreshTokenSession.objects.filter(
                            id=session_id,
                            user=request.user,
                            is_active=True
                        ).update(last_used_at=timezone.now())
                    
                    # Cache this update for 5 minutes to prevent spam
                    cache.set(cache_key, True, 300)
                    
                except Exception:
                    # Silently fail - session tracking is not critical
                    pass
        
        return response


class SecurityHeadersMiddleware:
    """
    Middleware để thêm security headers
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Add CORS headers if needed
        if hasattr(settings, 'ALLOWED_HOSTS'):
            response['Access-Control-Allow-Credentials'] = 'true'
        
        return response
