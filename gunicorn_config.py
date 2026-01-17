"""
Gunicorn Configuration File
============================

Production-ready configuration for Gunicorn WSGI server.

Usage:
    gunicorn config.wsgi:application --config gunicorn_config.py
"""

import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 5

# Logging
accesslog = "/home/restaurant/app/logs/gunicorn-access.log"
errorlog = "/home/restaurant/app/logs/gunicorn-error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "gunicorn-restaurant"

# Server mechanics
daemon = False
pidfile = "/home/restaurant/app/logs/gunicorn.pid"
user = None  # Run as current user (restaurant)
group = None
tmp_upload_dir = None

# SSL (if needed later)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"
