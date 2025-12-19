from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

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
    'apps.cart'
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
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=10),
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
    # Add static files serving for Swagger UI
    'SWAGGER_UI_DIST': 'SIDECAR',  # or your preferred CDN
    'REDOC_DIST': 'SIDECAR',  # or your preferred CDN
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