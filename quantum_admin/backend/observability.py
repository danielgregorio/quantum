"""
Observability: Structured Logging and Metrics
Provides comprehensive logging and metrics collection for production monitoring
"""

import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime
from functools import wraps

from pythonjsonlogger import jsonlogger
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# ============================================================================
# Structured JSON Logging
# ============================================================================

class StructuredLogger:
    """
    Structured JSON logger for production
    Outputs logs in JSON format for easy parsing and analysis
    """

    def __init__(self, name: str = "quantum_admin"):
        self.logger = logging.getLogger(name)
        self.setup_handler()

    def setup_handler(self):
        """Configure JSON logging handler"""
        handler = logging.StreamHandler()

        # JSON formatter
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )

        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def info(self, message: str, **kwargs):
        """Log info with extra context"""
        self.logger.info(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        """Log error with extra context"""
        self.logger.error(message, extra=kwargs, exc_info=True)

    def warning(self, message: str, **kwargs):
        """Log warning with extra context"""
        self.logger.warning(message, extra=kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug with extra context"""
        self.logger.debug(message, extra=kwargs)


# Singleton logger instance
_logger = None


def get_logger() -> StructuredLogger:
    """Get or create logger instance"""
    global _logger
    if _logger is None:
        _logger = StructuredLogger()
    return _logger


# ============================================================================
# Prometheus Metrics
# ============================================================================

class Metrics:
    """
    Prometheus metrics collector
    Tracks application performance and usage
    """

    # HTTP Request metrics
    http_requests_total = Counter(
        'http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )

    http_request_duration_seconds = Histogram(
        'http_request_duration_seconds',
        'HTTP request latency',
        ['method', 'endpoint']
    )

    http_requests_in_progress = Gauge(
        'http_requests_in_progress',
        'HTTP requests currently in progress'
    )

    # Database metrics
    db_queries_total = Counter(
        'db_queries_total',
        'Total database queries',
        ['operation']
    )

    db_query_duration_seconds = Histogram(
        'db_query_duration_seconds',
        'Database query duration',
        ['operation']
    )

    db_connections_active = Gauge(
        'db_connections_active',
        'Active database connections'
    )

    # AI/LLM metrics
    ai_requests_total = Counter(
        'ai_requests_total',
        'Total AI requests',
        ['provider']
    )

    ai_request_duration_seconds = Histogram(
        'ai_request_duration_seconds',
        'AI request duration',
        ['provider']
    )

    ai_tokens_used = Counter(
        'ai_tokens_used',
        'Total AI tokens used',
        ['provider']
    )

    # Docker metrics
    docker_operations_total = Counter(
        'docker_operations_total',
        'Docker operations',
        ['operation', 'status']
    )

    containers_running = Gauge(
        'containers_running',
        'Number of running containers'
    )

    # Authentication metrics
    auth_attempts_total = Counter(
        'auth_attempts_total',
        'Authentication attempts',
        ['status']
    )

    active_users = Gauge(
        'active_users',
        'Currently active users'
    )

    # Schema operations
    schema_inspections_total = Counter(
        'schema_inspections_total',
        'Schema inspection operations'
    )

    # Error metrics
    errors_total = Counter(
        'errors_total',
        'Total errors',
        ['error_type']
    )

    # Custom business metrics
    migrations_executed = Counter(
        'migrations_executed',
        'Database migrations executed'
    )

    pipeline_builds_total = Counter(
        'pipeline_builds_total',
        'Pipeline builds',
        ['status']
    )


# Singleton metrics instance
metrics = Metrics()


# ============================================================================
# Middleware for HTTP Metrics
# ============================================================================

class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP metrics
    Tracks request duration, status codes, and endpoints
    """

    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        # Track in-progress requests
        metrics.http_requests_in_progress.inc()

        # Start timer
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Record metrics
            duration = time.time() - start_time

            metrics.http_request_duration_seconds.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)

            metrics.http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()

            # Log request
            logger = get_logger()
            logger.info("HTTP request", extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration * 1000,
                "client": request.client.host if request.client else "unknown"
            })

            return response

        except Exception as e:
            # Log error
            logger = get_logger()
            logger.error(f"Request failed: {str(e)}", extra={
                "method": request.method,
                "path": request.url.path,
                "error": str(e)
            })

            metrics.errors_total.labels(error_type=type(e).__name__).inc()
            raise

        finally:
            # Decrement in-progress
            metrics.http_requests_in_progress.dec()


# ============================================================================
# Decorators for Function Metrics
# ============================================================================

def track_database_query(operation: str = "unknown"):
    """
    Decorator to track database queries

    Usage:
        @track_database_query("select_users")
        def get_users():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                duration = time.time() - start_time
                metrics.db_query_duration_seconds.labels(
                    operation=operation
                ).observe(duration)

                metrics.db_queries_total.labels(operation=operation).inc()

                logger = get_logger()
                logger.debug(f"Database query: {operation}", extra={
                    "operation": operation,
                    "duration_ms": duration * 1000
                })

                return result

            except Exception as e:
                logger = get_logger()
                logger.error(f"Database query failed: {operation}", extra={
                    "operation": operation,
                    "error": str(e)
                })
                raise

        return wrapper
    return decorator


def track_ai_request(provider: str = "unknown"):
    """
    Decorator to track AI requests

    Usage:
        @track_ai_request("ollama")
        def generate_text():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                duration = time.time() - start_time
                metrics.ai_request_duration_seconds.labels(
                    provider=provider
                ).observe(duration)

                metrics.ai_requests_total.labels(provider=provider).inc()

                return result

            except Exception as e:
                logger = get_logger()
                logger.error(f"AI request failed: {provider}", extra={
                    "provider": provider,
                    "error": str(e)
                })
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                duration = time.time() - start_time
                metrics.ai_request_duration_seconds.labels(
                    provider=provider
                ).observe(duration)

                metrics.ai_requests_total.labels(provider=provider).inc()

                return result

            except Exception as e:
                logger = get_logger()
                logger.error(f"AI request failed: {provider}", extra={
                    "provider": provider,
                    "error": str(e)
                })
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# Metrics Endpoint
# ============================================================================

def get_prometheus_metrics():
    """
    Get Prometheus metrics in exposition format
    Use this as FastAPI endpoint
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ============================================================================
# Utility Functions
# ============================================================================

def log_authentication_attempt(username: str, success: bool, **extra):
    """Log authentication attempt"""
    logger = get_logger()
    status = "success" if success else "failure"

    logger.info(f"Authentication attempt: {status}", extra={
        "username": username,
        "success": success,
        "timestamp": datetime.utcnow().isoformat(),
        **extra
    })

    metrics.auth_attempts_total.labels(status=status).inc()


def log_error(error_type: str, message: str, **extra):
    """Log structured error"""
    logger = get_logger()
    logger.error(message, extra={
        "error_type": error_type,
        "timestamp": datetime.utcnow().isoformat(),
        **extra
    })

    metrics.errors_total.labels(error_type=error_type).inc()


def log_docker_operation(operation: str, success: bool, **extra):
    """Log Docker operation"""
    logger = get_logger()
    status = "success" if success else "failure"

    logger.info(f"Docker operation: {operation}", extra={
        "operation": operation,
        "status": status,
        **extra
    })

    metrics.docker_operations_total.labels(
        operation=operation,
        status=status
    ).inc()


def update_container_count(count: int):
    """Update running container count"""
    metrics.containers_running.set(count)


def update_active_users(count: int):
    """Update active users count"""
    metrics.active_users.set(count)


def update_db_connections(count: int):
    """Update active database connections"""
    metrics.db_connections_active.set(count)


# ============================================================================
# Health Check with Metrics
# ============================================================================

def get_system_health() -> Dict[str, Any]:
    """
    Get system health with basic metrics
    Returns health status and key metrics
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "http_requests_in_progress": metrics.http_requests_in_progress._value.get(),
            "active_users": metrics.active_users._value.get(),
            "containers_running": metrics.containers_running._value.get(),
            "db_connections_active": metrics.db_connections_active._value.get()
        }
    }


# ============================================================================
# Example Usage
# ============================================================================

"""
USAGE EXAMPLES:

1. Structured Logging:
    from observability import get_logger

    logger = get_logger()
    logger.info("User logged in", user_id=123, username="john")
    logger.error("Database connection failed", error=str(e))

2. Track Database Query:
    @track_database_query("select_users")
    def get_all_users(db: Session):
        return db.query(User).all()

3. Track AI Request:
    @track_ai_request("ollama")
    def generate_text(prompt: str):
        return slm.generate(prompt)

4. Log Authentication:
    log_authentication_attempt("john", success=True, ip="192.168.1.1")

5. Update Metrics:
    update_container_count(5)
    update_active_users(120)

6. Metrics Endpoint (in main.py):
    from observability import get_prometheus_metrics

    @app.get("/metrics")
    def metrics():
        return get_prometheus_metrics()

7. Add Middleware (in main.py):
    from observability import MetricsMiddleware

    app.add_middleware(MetricsMiddleware)
"""
