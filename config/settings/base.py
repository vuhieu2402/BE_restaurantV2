from pathlib import Path
from decouple import config
import logging

# Get logger
logger = logging.getLogger(__name__)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# base.py is in config/settings/, so we need 3x parent to get to project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = None  # Phải được set trong environment-specific settings
DEBUG = None  # Phải được set trong environment-specific settings

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',  # OpenAPI/Swagger documentation
    'drf_spectacular_sidecar',  # Swagger UI static files
    'django_filters',  # Django filter backend
    'corsheaders',  # CORS support
    'channels',  # WebSocket support

    # Local apps
    'apps.users',
    'apps.dishes',
    'apps.restaurants',
    'apps.orders',
    'apps.reservations',
    'apps.payments',
    'apps.chat',
    'apps.analytics',
    'apps.authentications',
    'apps.salary_and_bonus',
    'apps.ratings',
    'apps.cart',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS middleware - phải đặt trước CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Custom auth middleware
    'apps.authentications.middleware.SessionTrackingMiddleware',
    'apps.authentications.middleware.SecurityHeadersMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Add global templates directory
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ASGI application for WebSocket support
ASGI_APPLICATION = 'config.asgi.application'

# Channels configuration for WebSocket
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(config('REDIS_HOST', default='127.0.0.1'), config('REDIS_PORT', default=6379, cast=int))],
        },
    },
}

# Cache configuration using Redis
# Using database 1 for cache (separate from Celery's database 0)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{config('REDIS_HOST', default='127.0.0.1')}:{config('REDIS_PORT', default=6379, cast=int)}/1",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'KEY_PREFIX': 'restaurant',
        'TIMEOUT': 3600,  # Default TTL: 1 hour
    }
}

REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'apps.api.exception_handler.custom_exception_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    # OpenAPI/Swagger Configuration
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'drf_spectacular.renderers.OpenApiJsonRenderer',
        'drf_spectacular.renderers.OpenApiYamlRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
}

# JWT Configuration
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,  # We use database tracking instead
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': None,  # Will be set in environment-specific settings
    'VERIFYING_KEY': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),

    # Custom settings for our database-based session tracking
    'AUTH_COOKIE': None,  # Don't use cookies
    'AUTH_COOKIE_DOMAIN': None,
    'AUTH_COOKIE_SECURE': False,
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_PATH': '/',
    'AUTH_COOKIE_SAMESITE': 'Lax',
}

# OpenAPI/Swagger Configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'Restaurant Management System API',
    'DESCRIPTION': 'Comprehensive restaurant management system with authentication, orders, reservations, and more.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/',
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': False,
        'displayOperationId': True,
    },
    'SWAGGER_UI_FAVICON_HREF': '/static/favicon.ico',
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton': False,
        'hideHostname': True,
        'noAutoAuth': False,
    },
    'PREPROCESSING_HOOKS': [],
    'POSTPROCESSING_HOOKS': [],
    'SERVERS': [
        {'url': 'http://localhost:8000', 'description': 'Development server'},
        {'url': 'https://api.restaurant.com', 'description': 'Production server'},
    ],
    'TAGS': [
        {'name': 'Authentication', 'description': 'User authentication and authorization'},
        {'name': 'Users', 'description': 'User management'},
        {'name': 'Cart', 'description': 'Shopping cart management'},
        {'name': 'Restaurants', 'description': 'Restaurant management'},
        {'name': 'Menu', 'description': 'Menu and dish management'},
        {'name': 'Orders', 'description': 'Order processing and management'},
        {'name': 'Reservations', 'description': 'Table reservations'},
        {'name': 'Payments', 'description': 'Payment processing'},
        {'name': 'Chat', 'description': 'Customer support chat'},
        {'name': 'Analytics', 'description': 'Analytics and reporting'},
    ],
    # Use drf-spectacular-sidecar for local static files (no CDN dependency)
    'SWAGGER_UI_DIST': 'SIDECAR',  # Use local sidecar static files
    'REDOC_DIST': 'SIDECAR',  # Use local sidecar static files
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ==================== STORAGE CONFIGURATION ====================
# AWS S3 / MinIO Storage Configuration
USE_S3 = config('USE_S3', default=False, cast=bool)

if USE_S3:
    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='ap-southeast-1')
    AWS_S3_CUSTOM_DOMAIN = config('AWS_S3_CUSTOM_DOMAIN', default=None)
    
    # S3 settings - NO ACL (use bucket policy instead)
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',  # Cache 1 day
    }
    AWS_S3_FILE_OVERWRITE = config('AWS_S3_FILE_OVERWRITE', default=False, cast=bool)
    AWS_DEFAULT_ACL = None  # Don't use ACLs - use bucket policy
    AWS_S3_USE_SSL = config('AWS_S3_USE_SSL', default=True, cast=bool)
    AWS_S3_VERIFY = config('AWS_S3_VERIFY', default=True, cast=bool)
    AWS_QUERYSTRING_AUTH = config('AWS_QUERYSTRING_AUTH', default=False, cast=bool)
    
    # Storage backend
    DEFAULT_FILE_STORAGE = 'config.storage.storage.MediaStorage'
    
    # Media URL
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
    else:
        MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/media/'
    
    logger.info(f"Using S3 storage: {AWS_STORAGE_BUCKET_NAME}")
    logger.info(f"Media URL: {MEDIA_URL}")
else:
    # Local storage fallback
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'
    logger.info("Using local file storage")

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# ==================== SMS CONFIGURATION ====================
# SMS Service Configuration for phone verification
# Supports multiple providers: twilio, vonage, local_sms

SMS_PROVIDER = config('SMS_PROVIDER', default='local_sms')  # Default to local SMS for development
SMS_ENABLED = config('SMS_ENABLED', default=False, cast=bool)

# # Twilio Configuration
# TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default=None)
# TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default=None)
# TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER', default=None)

# # Vonage (Nexmo) Configuration
# VONAGE_API_KEY = config('VONAGE_API_KEY', default=None)
# VONAGE_API_SECRET = config('VONAGE_API_SECRET', default=None)
# VONAGE_FROM_NUMBER = config('VONAGE_FROM_NUMBER', default=None)

# Local SMS Configuration (for development/testing)
LOCAL_SMS_DEBUG = config('LOCAL_SMS_DEBUG', default=True, cast=bool)
LOCAL_SMS_LOG_TO_CONSOLE = config('LOCAL_SMS_LOG_TO_CONSOLE', default=True, cast=bool)

# SMS Message Templates
SMS_TEMPLATES = {
    'verification': 'Ma xac thuc cua ban la: {code}. Hieu luc trong {minutes} phut.',
    'password_reset': 'Mat khau moi cua ban la: {code}. Hieu luc trong {minutes} phut.',
    'order_confirmation': 'Don hang {order_number} da duoc xac nhan. Thoi gian du kien: {time} phut.',
    'order_ready': 'Don hang {order_number} da san sang. Vui long den lay.',
    'reservation_reminder': 'Nho dat ban cho {guests} nguoi vao {time} ngay {date}.',
}

# SMS Rate Limiting
SMS_RATE_LIMIT_PER_MINUTE = config('SMS_RATE_LIMIT_PER_MINUTE', default=5, cast=int)
SMS_RATE_LIMIT_PER_HOUR = config('SMS_RATE_LIMIT_PER_HOUR', default=50, cast=int)
SMS_RATE_LIMIT_PER_DAY = config('SMS_RATE_LIMIT_PER_DAY', default=200, cast=int)

# Verification Code Rate Limiting (separate from SMS rate limiting)
VERIFICATION_RATE_LIMIT_PER_10MIN = config('VERIFICATION_RATE_LIMIT_PER_10MIN', default=3, cast=int)
VERIFICATION_RATE_LIMIT_PER_HOUR = config('VERIFICATION_RATE_LIMIT_PER_HOUR', default=10, cast=int)
VERIFICATION_RATE_LIMIT_PER_DAY = config('VERIFICATION_RATE_LIMIT_PER_DAY', default=20, cast=int)

# ==================== CORS CONFIGURATION ====================
# CORS settings for API access from frontend
# In development, allow all origins. In production, specify exact origins.

# CORS_ALLOWED_ORIGINS - List of allowed origins (for production)
# Example: CORS_ALLOWED_ORIGINS = ['https://example.com', 'https://www.example.com']

# CORS_ALLOW_ALL_ORIGINS - Allow all origins (ONLY for development!)
# Set to False in production and use CORS_ALLOWED_ORIGINS instead
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=True, cast=bool)

# CORS_ALLOW_CREDENTIALS - Allow cookies/auth headers
CORS_ALLOW_CREDENTIALS = config('CORS_ALLOW_CREDENTIALS', default=True, cast=bool)

# CORS_ALLOWED_HEADERS - Additional headers allowed in CORS requests
CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-session-id',
]

# CORS_ALLOWED_METHODS - HTTP methods allowed in CORS requests
CORS_ALLOWED_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# CORS_PREFLIGHT_MAX_AGE - Cache preflight requests for this many seconds
CORS_PREFLIGHT_MAX_AGE = 86400  # 24 hours


# ==================== VNPay CONFIGURATION ====================
# VNPay Payment Gateway Configuration
# https://sandbox.vnpayment.vn/merchant_webapi/api/transaction

# VNPay API Configuration
VNPAY_API_URL = config('VNPAY_API_URL', default='https://sandbox.vnpayment.vn/merchant_webapi/api/transaction')
VNPAY_PAYMENT_URL = config('VNPAY_PAYMENT_URL', default='https://sandbox.vnpayment.vn/paymentv2/vpcpay.html')
VNPAY_TMN_CODE = config('VNPAY_TMN_CODE', default='ENP3VCHI')
VNPAY_HASH_SECRET_KEY = config('VNPAY_HASH_SECRET_KEY', default='9HS0M7HREHKT5GF539YJJ8HSLC8LD0OF')
VNPAY_VERSION = config('VNPAY_VERSION', default='2.1.0')
VNPAY_COMMAND = config('VNPAY_COMMAND', default='pay')

# VNPay URLs Configuration
VNPAY_RETURN_URL = config('VNPAY_RETURN_URL', default='http://localhost:8000/api/payments/vnpay/return/')
VNPAY_CALLBACK_URL = config('VNPAY_CALLBACK_URL', default='http://localhost:8000/api/payments/vnpay/callback/')

# VNPay Payment Configuration
VNPAY_CURRENCY_CODE = config('VNPAY_CURRENCY_CODE', default='VND')
VNPAY_LOCALE = config('VNPAY_LOCALE', default='vn')
VNPAY_ORDER_TYPE = config('VNPAY_ORDER_TYPE', default='billpayment')

# VNPay Timeout Configuration (in seconds)
VNPAY_TIMEOUT = config('VNPAY_TIMEOUT', default=300, cast=int)  # 5 minutes

# VNPay Production Settings (set to True for production)
VNPAY_PRODUCTION = config('VNPAY_PRODUCTION', default=False, cast=bool)

# Override URLs for production
if VNPAY_PRODUCTION:
    VNPAY_API_URL = config('VNPAY_PRODUCTION_API_URL', default='https://vnpayment.vn/merchant_webapi/api/transaction')
    VNPAY_PAYMENT_URL = config('VNPAY_PRODUCTION_PAYMENT_URL', default='https://vnpayment.vn/paymentv2/vpcpay.html')


# ==================== LOGGING CONFIGURATION ====================
# Logging cơ bản - sẽ được override trong development.py và production.py
# Development: chỉ console logging (đơn giản)
# Production: file logging với rotation (phức tạp)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}