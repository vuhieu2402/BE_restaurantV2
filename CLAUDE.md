# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django 5.0 restaurant management system with REST API, WebSocket real-time communication, Celery background tasks, and AWS deployment. Supports three user roles: Customer, Staff, Manager (plus Admin).

## Development Commands

### Running the Development Server
```bash
# Start Django development server
python manage.py runserver

# Using Docker Compose (full stack with Redis, MinIO, Celery)
docker-compose up

# Start specific services
docker-compose up django redis postgres celery_worker
```

### Database Operations
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Access Django Admin: http://localhost:8000/admin/
```

### Celery Tasks
```bash
# Start Celery worker (uses queue-specific routing)
celery -A config.celery worker --loglevel=info --queues=auth,notifications,analytics,orders,default

# Start Celery Beat scheduler
celery -A config.celery beat --loglevel=info

# Start Flower monitoring UI (port 5555)
celery -A config.celery flower --port=5555
```

### WebSocket (Daphne)
```bash
# Start Daphne ASGI server for WebSocket support
daphne -b 127.0.0.1 -p 8001 config.asgi:application
```

### Testing
```bash
# Run all tests
python manage.py test

# Run tests for specific app
python manage.py test apps.users

# Run specific test class or method
python manage.py test apps.users.tests.test_views
```

### Static Files and Media
```bash
# Collect static files
python manage.py collectstatic
```

## Architecture

### Directory Structure

```
apps/                    # Django applications (domain-oriented)
  ├─ analytics/         # Analytics, reports
  ├─ authentications/   # JWT auth, session tracking
  ├─ cart/             # Shopping cart
  ├─ chat/             # WebSocket chat, chatbot (OpenAI/Groq)
  ├─ dishes/           # Menu, categories, dishes
  ├─ orders/           # Order management (WebSocket updates)
  ├─ payments/         # VNPay payment integration
  ├─ ratings/          # Customer reviews
  ├─ reservations/     # Table reservations
  ├─ restaurants/      # Restaurant profile, settings
  ├─ salary_and_bonus/ # Employee payroll
  ├─ users/            # User management
  └─ api/              # Shared utilities (exception handler, response, pagination)
config/                 # Django settings and configuration
  ├─ settings/          # Environment-specific settings (base.py, development.py, production.py)
  ├─ asgi.py           # ASGI config for WebSocket (Daphne)
  ├─ wsgi.py           # WSGI config for HTTP (Gunicorn)
  └─ celery.py         # Celery configuration with queue routing
docker/                 # Docker-related configs
requirements/           # Python dependencies
scripts/               # Utility scripts (Supervisor setup, S3 migration)
supervisor/            # Process monitoring configs
```

### Application Structure Pattern

Each Django app follows this pattern:
- `models.py` - Django models (use `selectors.py` for complex queries)
- `serializers.py` - DRF serializers
- `views.py` - ViewSets and API views
- `urls.py` - URL routing
- `services.py` - Business logic (layered architecture)
- `selectors.py` - Data access layer (query logic)
- `admin.py` - Django admin configuration
- `tests.py` - Tests
- `middleware.py` - Custom middleware (if needed)
- `routing.py` - WebSocket routing (for chat, orders)
- `consumers.py` - WebSocket consumers (for chat, orders)

### Settings Hierarchy

Settings use multi-environment pattern:
- `config/settings/base.py` - Base settings shared across environments
- `config/settings/development.py` - Development overrides
- `config/settings/production.py` - Production overrides

Default settings module in `manage.py` is `config.settings.development`.

### Server Configuration

**Production setup uses dual servers:**
- Gunicorn (WSGI, port 8000) - Handles HTTP REST API
- Daphne (ASGI, port 8001) - Handles WebSocket connections
- Nginx (port 80/443) - Reverse proxy routes to Gunicorn/Daphne

Configuration files:
- `gunicorn_config.py` - Gunicorn settings
- `daphne_config.py` - Daphne settings
- `supervisor/` - Process monitoring configs (for production)

### Celery Task Queue Routing

Tasks are routed to specific queues for better scaling:
- `auth` - Authentication tasks (email verification, SMS)
- `notifications` - Email notifications
- `analytics` - Analytics report generation
- `orders` - Order processing tasks
- `chatbot` - Chatbot tasks
- `default` - General tasks

Worker command includes specific queues: `--queues=auth,notifications,analytics,orders,default`

### WebSocket Architecture

WebSocket consumers use JWT authentication middleware:
- `apps.chat.middleware.JWTAuthMiddlewareStack` - Validates JWT tokens for WebSocket connections
- Consumers located in `apps/chat/consumers.py` and `apps/orders/consumers.py`
- Routing defined in each app's `routing.py`

### Key Integrations

**Authentication:**
- JWT tokens via `djangorestframework-simplejwt`
- Custom user model (`apps.users.models.User`)
- Session tracking middleware (`apps.authentications.middleware.SessionTrackingMiddleware`)
- Database-based refresh token tracking

**Storage:**
- AWS S3 or MinIO for media files
- Configured via `config/storage/storage.py`
- Controlled by `USE_S3` environment variable
- Local storage fallback when `USE_S3=False`

**Payment:**
- VNPay payment gateway integration (`apps.payments`)
- Sandbox mode vs production controlled by `VNPAY_PRODUCTION`

**Cache:**
- Redis for caching (database 1), Celery broker (database 0)
- Configured in `config/settings/base.py` CACHES section

### API Documentation

- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- OpenAPI Schema: `/api/schema/`
- Uses `drf-spectacular` for auto-generation

### Standard Response Format

All APIs use `ApiResponse` from `apps.api.response.py`:
```python
return ApiResponse.success(data={...})         # 200
return ApiResponse.created(data={...})         # 201
return ApiResponse.bad_request(message="...")   # 400
return ApiResponse.validation_error(errors={}) # 422
return ApiResponse.unauthorized(message="...")  # 401
return ApiResponse.forbidden(message="...")     # 403
return ApiResponse.not_found(message="...")     # 404
return ApiResponse.error(message="...")         # 500
```

### Custom Exception Handling

Uses `custom_exception_handler` from `apps.api.exception_handler.py`:
- Sanitizes sensitive information in production
- Logs detailed errors server-side
- Returns user-friendly messages to clients
- Custom exceptions: `CustomAPIException`

### Layered Architecture Pattern

- **Views** - Handle HTTP request/response, call services
- **Services** - Business logic, coordinate between models
- **Selectors** - Data access layer, complex queries
- **Models** - Database schema, basic methods

Example:
```python
# views.py
def my_view(request):
    result = MyService.process_data(request.user.id)

# services.py
def process_data(user_id):
    data = MySelector.get_user_data(user_id)
    # business logic here
    return result

# selectors.py
def get_user_data(user_id):
    return User.objects.filter(id=user_id).select_related(...)
```

### Environment Variables

Key environment variables (see `config/settings/base.py`):
- `DJANGO_SETTINGS_MODULE` - Settings module to use
- `DEBUG` - Debug mode
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - PostgreSQL
- `REDIS_HOST`, `REDIS_PORT` - Redis
- `USE_S3`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME` - S3
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` - Celery
- `VNPAY_*` - VNPay configuration
- `SMS_PROVIDER`, `SMS_ENABLED` - SMS configuration
- `EMAIL_*` - Email configuration

### Important Notes

- Custom user model: `AUTH_USER_MODEL = 'users.User'`
- Timezone: `UTC` (can be changed in settings)
- Celery beat tasks defined in `config/celery.py`
- WebSocket routes combined from multiple apps in `config/asgi.py`
- Use `python-decouple` for environment variables
- CORS configured for frontend integration
