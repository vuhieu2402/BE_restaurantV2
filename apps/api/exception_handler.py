from rest_framework.views import exception_handler
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.conf import settings
from rest_framework.exceptions import (
    APIException,
    ValidationError,
    NotFound,
    PermissionDenied as DRFPermissionDenied,
    AuthenticationFailed,
    NotAuthenticated,
    ParseError
)
import logging
import traceback
import sys

logger = logging.getLogger(__name__)


def _sanitize_error_data(error_data, is_debug=False):
    """
    Sanitize error data to remove sensitive information in production
    
    Args:
        error_data: Original error data (dict, list, or string)
        is_debug: Whether debug mode is enabled
    
    Returns:
        Sanitized error data safe to send to client
    """
    if is_debug:
        # In debug mode, return full error details
        return error_data
    
    # In production, sanitize sensitive information
    if isinstance(error_data, dict):
        sanitized = {}
        sensitive_keys = ['traceback', 'stack', 'file', 'path', 'sql', 'query', 
                         'password', 'secret', 'key', 'token', 'credential']
        
        for key, value in error_data.items():
            key_lower = key.lower()
            # Check if key contains sensitive keywords
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "[Hidden for security]"
            elif isinstance(value, (dict, list)):
                sanitized[key] = _sanitize_error_data(value, is_debug)
            else:
                # Remove file paths and system paths
                if isinstance(value, str):
                    # Remove absolute paths
                    if '/' in value or '\\' in value:
                        sanitized[key] = "An error occurred"
                    else:
                        sanitized[key] = value
                else:
                    sanitized[key] = value
        return sanitized
    
    elif isinstance(error_data, list):
        return [_sanitize_error_data(item, is_debug) for item in error_data]
    
    elif isinstance(error_data, str):
        # Remove file paths and sensitive info
        if '/' in error_data or '\\' in error_data:
            return "An error occurred"
        return error_data
    
    return error_data


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that returns standardized error responses
    
    Security Features:
    - Hides sensitive information (stack traces, file paths, SQL queries) in production
    - Logs detailed error information on server side
    - Returns user-friendly error messages to client
    
    Usage:
        In settings.py:
        REST_FRAMEWORK = {
            'EXCEPTION_HANDLER': 'api.exception_handler.custom_exception_handler',
        }
    """
    from apps.api.response import ApiResponse
    
    # Get debug mode from settings
    is_debug = getattr(settings, 'DEBUG', False)
    
    # Extract request info for logging
    request = context.get('request') if context else None
    view = context.get('view') if context else None
    
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)
    
    # If DRF handled it, format it according to our standard
    if response is not None:
        # Extract error details
        error_data = response.data
        error_message = str(exc)
        
        # Log detailed error information (always log, even in production)
        logger.error(
            f"API Exception: {type(exc).__name__}",
            extra={
                'exception_type': type(exc).__name__,
                'exception_message': str(exc),
                'view': view.__class__.__name__ if view else None,
                'request_path': request.path if request else None,
                'request_method': request.method if request else None,
                'user': str(request.user) if request and hasattr(request, 'user') else None,
                'error_data': error_data,
                'traceback': traceback.format_exc() if is_debug else None,
            },
            exc_info=True
        )
        
        # Sanitize error data for client response
        sanitized_error_data = _sanitize_error_data(error_data, is_debug)
        
        # Handle different exception types
        if isinstance(exc, ValidationError):
            # Validation errors - use 422 status
            # Validation errors are usually safe to show
            return ApiResponse.validation_error(
                message="Validation error",
                errors=sanitized_error_data if not is_debug else error_data
            )
        elif isinstance(exc, (NotFound, Http404)):
            return ApiResponse.not_found(
                message=error_message if is_debug else "Resource not found",
                errors=sanitized_error_data
            )
        elif isinstance(exc, (DRFPermissionDenied, PermissionDenied)):
            return ApiResponse.forbidden(
                message=error_message if is_debug else "Permission denied",
                errors=sanitized_error_data
            )
        elif isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            return ApiResponse.unauthorized(
                message=error_message if is_debug else "Authentication required",
                errors=sanitized_error_data
            )
        elif isinstance(exc, ParseError):
            # JSON parsing errors - provide clear message
            return ApiResponse.bad_request(
                message="Invalid JSON format. Please check your request body syntax.",
                errors={"detail": error_message} if is_debug else None
            )
        elif isinstance(exc, APIException):
            # Generic API exception
            status_code = exc.status_code
            return ApiResponse.error(
                message=error_message if is_debug else "An error occurred",
                errors=sanitized_error_data,
                status_code=status_code
            )
        else:
            # Fallback for other DRF exceptions
            return ApiResponse.error(
                message=error_message if is_debug else "An error occurred",
                errors=sanitized_error_data,
                status_code=response.status_code
            )
    
    # Handle Django exceptions that DRF doesn't catch
    if isinstance(exc, DjangoValidationError):
        error_data = exc.message_dict if hasattr(exc, 'message_dict') else str(exc)
        sanitized = _sanitize_error_data(error_data, is_debug)
        
        logger.warning(
            f"Django ValidationError: {str(exc)}",
            extra={
                'exception_type': 'DjangoValidationError',
                'error_data': error_data,
            }
        )
        
        return ApiResponse.validation_error(
            message="Validation error",
            errors=sanitized if not is_debug else error_data
        )
    
    if isinstance(exc, Http404):
        logger.warning(
            f"Http404: {str(exc)}",
            extra={
                'request_path': request.path if request else None,
            }
        )
        return ApiResponse.not_found(
            message="Resource not found"
        )
    
    if isinstance(exc, PermissionDenied):
        logger.warning(
            f"PermissionDenied: {str(exc)}",
            extra={
                'user': str(request.user) if request and hasattr(request, 'user') else None,
                'request_path': request.path if request else None,
            }
        )
        return ApiResponse.forbidden(
            message="Permission denied"
        )
    
    # Log unexpected exceptions with full details
    logger.exception(
        "Unhandled exception in API",
        extra={
            'exception_type': type(exc).__name__,
            'exception_message': str(exc),
            'view': view.__class__.__name__ if view else None,
            'request_path': request.path if request else None,
            'request_method': request.method if request else None,
            'user': str(request.user) if request and hasattr(request, 'user') else None,
            'traceback': traceback.format_exc(),
        }
    )
    
    # Return generic error for unhandled exceptions
    # NEVER expose actual error details to client in production
    if is_debug:
        # In debug mode, show error details for development
        return ApiResponse.error(
            message=f"An unexpected error occurred: {str(exc)}",
            errors={"detail": str(exc), "traceback": traceback.format_exc()},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    else:
        # In production, hide all error details
        return ApiResponse.error(
            message="An unexpected error occurred. Please contact support if the problem persists.",
            errors=None,  # Don't expose any error details
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class CustomAPIException(APIException):
    """
    Custom API exception with standardized error format
    
    Usage:
        raise CustomAPIException(
            message="Custom error message",
            errors={"field": "Error detail"},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "An error occurred"
    default_code = "error"
    
    def __init__(self, message=None, errors=None, status_code=None):
        if status_code is not None:
            self.status_code = status_code
        if message is not None:
            self.detail = message
        else:
            self.detail = self.default_detail
        
        self.errors = errors or {}
        super().__init__(self.detail)

