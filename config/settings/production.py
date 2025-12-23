"""
Production settings - cho môi trường production
Sử dụng: export DJANGO_SETTINGS_MODULE=config.settings.production
Hoặc set trong WSGI/ASGI server
"""
from .base import *
from decouple import config, Csv

DEBUG = config('DEBUG', default=False, cast=bool)

SECRET_KEY = config('SECRET_KEY')

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

# JWT Signing Key for production
SIMPLE_JWT['SIGNING_KEY'] = SECRET_KEY
SIMPLE_JWT['VERIFYING_KEY'] = None

# Email Configuration for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@restaurant.com')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Security headers for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ==================== DATABASE CONFIGURATION ====================
# PostgreSQL cho production (bắt buộc)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432', cast=int),
        'OPTIONS': {
            'connect_timeout': 10,
        },
        # Connection pooling (optional, nếu dùng pgBouncer hoặc tương tự)
        # 'CONN_MAX_AGE': 600,
    }
}

# ==================== MINIO/STORAGE CONFIGURATION ====================
# MinIO Object Storage cho media files (bắt buộc trong production)

AWS_ACCESS_KEY_ID = config('MINIO_ACCESS_KEY')
AWS_SECRET_ACCESS_KEY = config('MINIO_SECRET_KEY')
AWS_STORAGE_BUCKET_NAME = config('MINIO_BUCKET_NAME')
AWS_S3_ENDPOINT_URL = config('MINIO_ENDPOINT_URL')
AWS_S3_CUSTOM_DOMAIN = config('MINIO_CUSTOM_DOMAIN', default=None)

# S3 settings
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',  # Cache 1 ngày
}
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = 'public-read'
AWS_S3_USE_SSL = config('MINIO_USE_SSL', default=True, cast=bool)
AWS_S3_VERIFY = config('MINIO_VERIFY_SSL', default=True, cast=bool)

# Storage backend
DEFAULT_FILE_STORAGE = 'config.storage.storage.MinIOMediaStorage'

# Media URL
if AWS_S3_CUSTOM_DOMAIN:
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
else:
    MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/media/'

# ==================== PRODUCTION LOGGING ====================
# Logging phức tạp - ghi vào files với rotation
# Quan trọng cho monitoring và debugging production issues

import os
LOGS_DIR = BASE_DIR / 'logs'  # Fixed: use BASE_DIR directly (not .parent)
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'detailed': {
            'format': '{levelname} {asctime} [{name}] {pathname}:{lineno} {funcName}() {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        # Console handler - vẫn giữ để xem logs trong container/server logs
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        # File handler - ghi tất cả logs vào file
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        # Error file handler - chỉ ghi errors và critical
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'errors.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 10,  # Giữ nhiều backup hơn cho errors
            'formatter': 'detailed',
        },
        # API specific handler - ghi logs từ API app
        'api_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'api.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'detailed',
        },

    },
    'loggers': {
        # Django logger
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Django request logger - chỉ log errors
        'django.request': {
            'handlers': ['error_file', 'api_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        # Django server logger
        'django.server': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        # API app logger - quan trọng nhất cho API errors
        'api': {
            'handlers': ['console', 'api_file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'api.exception_handler': {
            'handlers': ['api_file', 'error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        # Root logger
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    },
}

# Production security settings
if not DEBUG:
    # Security settings
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    