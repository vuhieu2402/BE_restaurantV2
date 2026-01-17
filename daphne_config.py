"""
Daphne (ASGI Server) Configuration for WebSocket Support
=========================================================

Daphne handles WebSocket connections and ASGI requests.
This runs separately from Gunicorn (WSGI server).

Usage:
    daphne -b 127.0.0.1 -p 8001 config.asgi:application
"""

# Server Socket
bind = "127.0.0.1:8001"
websocket_timeout = 86400  # 24 hours for long-lived connections
ping_interval = 20  # Send ping every 20 seconds
ping_timeout = 10  # Wait 10 seconds for pong response

# Application
application_close_timeout = 60  # Timeout for closing connections

# Logging
verbosity = 1  # 0=ERROR, 1=INFO, 2=DEBUG
access_log = "/home/restaurant/app/logs/daphne-access.log"
error_log = "/home/restaurant/app/logs/daphne-error.log"

# Process naming
proc_name = "daphne-restaurant"

# Note: Daphne doesn't support all Gunicorn options
# Some settings are applied via command-line arguments
