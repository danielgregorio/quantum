"""
Gunicorn configuration for Quantum Framework

This file is used by the systemd services to configure Gunicorn.
Can be customized per environment by setting environment variables.
"""

import os
import multiprocessing

# Server socket
bind = os.environ.get('GUNICORN_BIND', '127.0.0.1:8090')
backlog = 2048

# Worker processes
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 2
max_requests = 1000
max_requests_jitter = 50

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Logging
errorlog = os.environ.get('GUNICORN_ERROR_LOG', '-')
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'quantum'

# Hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    pass

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    pass

def when_ready(server):
    """Called just after the server is started."""
    pass

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    pass

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    pass

def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT."""
    pass

def worker_abort(worker):
    """Called when a worker receives SIGABRT."""
    pass

def pre_exec(server):
    """Called just before a new master process is forked."""
    pass

def child_exit(server, worker):
    """Called when a worker is killed."""
    pass

def worker_exit(server, worker):
    """Called when a worker exits."""
    pass

def nworkers_changed(server, new_value, old_value):
    """Called when the number of workers changes."""
    pass

def on_exit(server):
    """Called just before exiting gunicorn."""
    pass
