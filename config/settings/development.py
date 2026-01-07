"""
Development settings - cho môi trường phát triển
Sử dụng: python manage.py runserver (mặc định dùng base.py)
Hoặc: export DJANGO_SETTINGS_MODULE=config.settings.development
"""
from .base import *
from decouple import config, Csv

# SECURITY WARNING: don't use in production!
DEBUG = config('DEBUG', default=True, cast=bool)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-957@tc^2!5b$qmo9+ao)=i%#5)3ayw3lt9$legdp$0u&bau*pi')

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,[::1]', cast=Csv())

# ==================== DATABASE CONFIGURATION ====================
# PostgreSQL cho development (bắt buộc)
# Sử dụng python-decouple để đọc .env file và environment variables

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='restaurants'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='240211'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432', cast=int),
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}

# ==================== MINIO/STORAGE CONFIGURATION ====================
# MinIO Object Storage cho media files
# Tất cả ảnh sẽ được lưu vào MinIO, DB chỉ lưu đường dẫn

USE_MINIO = config('USE_MINIO', default=True, cast=bool)

if USE_MINIO:
    # AWS S3 compatible settings (cho MinIO)
    AWS_ACCESS_KEY_ID = config('MINIO_ACCESS_KEY', default='minioadmin')
    AWS_SECRET_ACCESS_KEY = config('MINIO_SECRET_KEY', default='minioadmin123')
    AWS_STORAGE_BUCKET_NAME = config('MINIO_BUCKET_NAME', default='restaurant-media')
    AWS_S3_ENDPOINT_URL = config('MINIO_ENDPOINT_URL', default='http://localhost:9000')
    AWS_S3_CUSTOM_DOMAIN = config('MINIO_CUSTOM_DOMAIN', default=None)
    
    # S3 settings
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',  # Cache 1 ngày
    }
    AWS_S3_FILE_OVERWRITE = False  # Không overwrite file cùng tên
    AWS_DEFAULT_ACL = 'public-read'  # Public read
    AWS_S3_USE_SSL = False  # MinIO local không dùng SSL
    AWS_S3_VERIFY = False  # Không verify SSL certificate
    
    # Storage backend
    DEFAULT_FILE_STORAGE = 'config.storage.storage.MinIOMediaStorage'
    
    # Media URL sẽ trỏ tới MinIO
    MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/media/'
else:
    # Fallback về local storage nếu không dùng MinIO
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

# JWT Signing Key for development
SIMPLE_JWT['SIGNING_KEY'] = SECRET_KEY
SIMPLE_JWT['VERIFYING_KEY'] = None

# Email Configuration for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Hiển thị email trên console
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# For real email testing, uncomment and configure:
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
# EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# ==================== LOGGING DIRECTORY ====================
# Tạo thư mục logs nếu chưa tồn tại
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# ==================== DEVELOPMENT LOGGING ====================
# Logging với cả console và file - ghi logs để debug
# File logging giúp theo dõi lịch sử API calls

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} [{name}] {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'detailed': {
            'format': '{levelname} {asctime} [{name}] {module}:{funcName}:{lineno}\n{message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',  # Hiển thị tất cả logs khi develop
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        # File handler - ghi tất cả logs vào file
        'file': {
            'level': 'DEBUG',
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
            'backupCount': 10,
            'formatter': 'detailed',
        },
        # API specific handler - ghi logs từ API app
        'api_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'api.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'detailed',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG',  # Xem tất cả request errors
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        # API logger - ghi đầy đủ khi develop
        'api': {
            'handlers': ['console', 'api_file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'api.exception_handler': {
            'handlers': ['console', 'api_file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Tắt DEBUG logs cho các thư viện bên ngoài
        'botocore': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'boto3': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        's3transfer': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'urllib3': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Storage logger
        'config.storage': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Root logger
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    },
}

# ==================== CORS CONFIGURATION FOR DEVELOPMENT ====================
# Allow all origins in development for easier testing
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Development tools
if DEBUG:
    # Thêm các tools hữu ích cho development
    INSTALLED_APPS += [
        # 'debug_toolbar',  # Uncomment nếu cài django-debug-toolbar
    ]

    MIDDLEWARE += [
        # 'debug_toolbar.middleware.DebugToolbarMiddleware',  # Uncomment nếu cài
    ]

    # Debug toolbar settings (nếu sử dụng)
    # INTERNAL_IPS = ['127.0.0.1']

    # Serve static files during development
    STATICFILES_DIRS = [
        BASE_DIR / 'static',
    ]

    # Static files configuration for development
    STATIC_URL = '/static/'
    STATIC_ROOT = BASE_DIR / 'staticfiles'

