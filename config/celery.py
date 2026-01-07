"""
Celery Configuration for Restaurant Management System
Asynchronous task processing for email sending, SMS, and background operations
"""
import os
import sys
from celery import Celery
from celery.schedules import crontab
from django.conf import settings
from decouple import config

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('restaurant')

# Windows-specific configuration
# Celery has issues with prefork pool on Windows, use solo pool instead
if sys.platform == 'win32':
    os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all Django apps
app.autodiscover_tasks()

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

app.conf.update(
    # Broker settings
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,

    # Task execution settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Ho_Chi_Minh',
    enable_utc=True,

    # Task routing for different queues
    task_routes={
        'apps.authentications.tasks.*': {'queue': 'auth'},
        'apps.notifications.tasks.*': {'queue': 'notifications'},
        'apps.analytics.tasks.*': {'queue': 'analytics'},
        'apps.orders.tasks.*': {'queue': 'orders'},
        'apps.chat.tasks.*': {'queue': 'chatbot'},
    },

    # Queue definitions
    task_default_queue='default',
    task_queues={
        'default': {
            'exchange': 'default',
            'routing_key': 'default',
        },
        'auth': {
            'exchange': 'auth',
            'routing_key': 'auth',
        },
        'notifications': {
            'exchange': 'notifications',
            'routing_key': 'notifications',
        },
        'analytics': {
            'exchange': 'analytics',
            'routing_key': 'analytics',
        },
        'orders': {
            'exchange': 'orders',
            'routing_key': 'orders',
        },
        'chatbot': {
            'exchange': 'chatbot',
            'routing_key': 'chatbot',
        },
    },

    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    
    # Windows compatibility - use solo pool on Windows
    worker_pool='solo' if sys.platform == 'win32' else 'prefork',
    worker_concurrency=1 if sys.platform == 'win32' else 4,

    # Task retry settings
    task_default_max_retries=3,
    task_default_retry_delay=60,  # seconds

    # Task execution time limits
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes

    # Result settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
    },

    # Beat scheduler settings for periodic tasks
    beat_schedule={
        # Clean up expired verification codes every 10 minutes
        'cleanup-expired-verification-codes': {
            'task': 'apps.authentications.tasks.cleanup_expired_verification_codes',
            'schedule': crontab(minute='*/10'),  # Every 10 minutes
        },

        # Clean up expired refresh tokens every hour
        'cleanup-expired-refresh-tokens': {
            'task': 'apps.authentications.tasks.cleanup_expired_refresh_tokens',
            'schedule': crontab(minute=0, hour='*/1'),  # Every hour
        },

        # Generate daily analytics reports
        'generate-daily-analytics': {
            'task': 'apps.analytics.tasks.generate_daily_report',
            'schedule': crontab(minute=0, hour=1),  # 1:00 AM daily
        },

        # Send reservation reminders
        'send-reservation-reminders': {
            'task': 'apps.reservations.tasks.send_reservation_reminders',
            'schedule': crontab(minute='*/30'),  # Every 30 minutes
        },

        # Clean up old chatbot conversation contexts (daily at 2 AM)
        'cleanup-old-chatbot-contexts': {
            'task': 'apps.chat.tasks.cleanup_old_conversation_context',
            'schedule': crontab(minute=0, hour=2),  # 2:00 AM daily
        },
    },

    # Monitoring settings
    worker_send_task_events=True,
    task_send_sent_event=True,

    # Security settings
    worker_hijack_root_logger=False,
    worker_log_color=False,
)

# Security middleware for production
if not config('DEBUG', default=False, cast=bool):
    app.conf.update(
        # Use SSL for broker connections in production
        broker_use_ssl={
            'ssl_cert_reqs': None,
        },
        # Use SSL for result backend in production
        result_backend_use_ssl={
            'ssl_cert_reqs': None,
        },
    )

@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery connectivity"""
    print(f'Request: {self.request!r}')


# Celery signals for better error handling
from celery.signals import task_prerun, task_postrun, task_failure
import logging

logger = logging.getLogger(__name__)

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Log task start"""
    logger.info(f"Task started: {task.name}[{task_id}] with args={args}, kwargs={kwargs}")

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, **kwds):
    """Log task completion"""
    logger.info(f"Task completed: {task.name}[{task_id}] with result={retval}")

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Log task failures"""
    logger.error(f"Task failed: {sender.name}[{task_id}] - {exception}")