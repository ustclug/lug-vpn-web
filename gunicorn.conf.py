# Gunicorn configuration for lug-vpn-web
# https://docs.gunicorn.org/en/stable/settings.html

import os

# Server socket
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:5000")

# Worker processes
workers = int(os.environ.get("GUNICORN_WORKERS", "4"))
worker_class = "sync"
threads = int(os.environ.get("GUNICORN_THREADS", "2"))

# Timeouts
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
graceful_timeout = 10
keepalive = 2

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "lugvpn-web"

# Server mechanics
preload_app = True
daemon = False
