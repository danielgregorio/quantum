"""
Quantum Python Bridge

Provides the magical 'q' object that connects Python code to the Quantum context.
This bridge allows seamless interaction between embedded Python code and the
Quantum runtime environment.

Usage in q:python blocks:
    <q:python>
        # Access variables
        user_id = q.user_id
        q.result = calculate(user_id)

        # Database queries
        users = q.query('SELECT * FROM users WHERE active = :active', active=True)

        # HTTP requests
        response = q.get('https://api.example.com/data')

        # Message queue
        q.publish('orders.created', order_data)

        # Logging
        q.info('Processing complete')
    </q:python>
"""

import json
import time
import threading
from typing import Any, Dict, Optional, List, Callable, Union
from dataclasses import dataclass, field


class QuantumBridgeError(Exception):
    """Base exception for bridge errors"""
    pass


class QuantumBridge:
    """
    The magical 'q' object - bridge between Python and Quantum.

    This object is automatically available in all q:python blocks and provides
    access to:
    - Component variables (read/write)
    - Database queries
    - HTTP requests
    - Message queue operations
    - Job dispatching
    - Caching
    - Session management
    - Logging
    - And more...
    """

    def __init__(
        self,
        context: Any,
        services: Optional[Dict[str, Any]] = None,
        request: Optional[Any] = None
    ):
        """
        Initialize the bridge.

        Args:
            context: The Quantum execution context
            services: Optional dict of services (db, cache, broker, etc.)
            request: Optional HTTP request object
        """
        object.__setattr__(self, '_context', context)
        object.__setattr__(self, '_services', services or {})
        object.__setattr__(self, '_request', request)
        object.__setattr__(self, '_exports', {})
        object.__setattr__(self, '_local', threading.local())

    # =========================================================================
    # Variable Access (q.variable / q.variable = value)
    # =========================================================================

    def __getattr__(self, name: str) -> Any:
        """
        Get a variable from the Quantum context.

        Usage:
            user_id = q.user_id
            items = q.cart_items
        """
        # Check exports first
        exports = object.__getattribute__(self, '_exports')
        if name in exports:
            return exports[name]

        # Then check context
        context = object.__getattribute__(self, '_context')
        if hasattr(context, 'get'):
            return context.get(name)
        elif hasattr(context, 'variables'):
            return context.variables.get(name)
        elif isinstance(context, dict):
            return context.get(name)

        raise AttributeError(f"Variable '{name}' not found in Quantum context")

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Set a variable in the Quantum context.

        Usage:
            q.result = 42
            q.user_data = {'name': 'John'}
        """
        context = object.__getattribute__(self, '_context')
        if hasattr(context, 'set'):
            context.set(name, value)
        elif hasattr(context, 'variables'):
            context.variables[name] = value
        elif isinstance(context, dict):
            context[name] = value
        else:
            # Store in exports
            exports = object.__getattribute__(self, '_exports')
            exports[name] = value

    def get(self, name: str, default: Any = None) -> Any:
        """
        Get a variable with optional default.

        Usage:
            value = q.get('optional_var', 'default_value')
        """
        try:
            return self.__getattr__(name)
        except AttributeError:
            return default

    def set(self, name: str, value: Any) -> None:
        """
        Explicitly set a variable.

        Usage:
            q.set('result', computed_value)
        """
        self.__setattr__(name, value)

    def export(self, name: str, value: Any) -> None:
        """
        Export a variable from isolated scope to component scope.

        Usage (in isolated scope):
            temp = calculate()
            q.export('result', temp)
        """
        exports = object.__getattribute__(self, '_exports')
        exports[name] = value
        # Also set in context
        self.__setattr__(name, value)

    def get_exports(self) -> Dict[str, Any]:
        """Get all exported variables."""
        return dict(object.__getattribute__(self, '_exports'))

    # =========================================================================
    # Database Queries (q.query, q.fetch, q.execute)
    # =========================================================================

    def query(self, sql: str, **params) -> Any:
        """
        Execute a SQL query and return results.

        Usage:
            users = q.query('SELECT * FROM users WHERE active = :active', active=True)
            for user in users:
                print(user['name'])
        """
        services = object.__getattribute__(self, '_services')
        db = services.get('db') or services.get('database')

        if db is None:
            raise QuantumBridgeError("Database service not available")

        if hasattr(db, 'execute_query'):
            return db.execute_query(sql, params)
        elif hasattr(db, 'execute'):
            return db.execute(sql, params)
        else:
            raise QuantumBridgeError("Database service doesn't support query execution")

    def fetch(self, sql: str, **params) -> List[Dict[str, Any]]:
        """
        Execute query and fetch all results as list of dicts.

        Usage:
            users = q.fetch('SELECT * FROM users')
        """
        result = self.query(sql, **params)
        if hasattr(result, 'fetchall'):
            return [dict(row) for row in result.fetchall()]
        return list(result) if result else []

    def fetchone(self, sql: str, **params) -> Optional[Dict[str, Any]]:
        """
        Execute query and fetch first result.

        Usage:
            user = q.fetchone('SELECT * FROM users WHERE id = :id', id=1)
        """
        result = self.query(sql, **params)
        if hasattr(result, 'fetchone'):
            row = result.fetchone()
            return dict(row) if row else None
        return result[0] if result else None

    def execute(self, sql: str, **params) -> int:
        """
        Execute SQL statement (INSERT, UPDATE, DELETE) and return affected rows.

        Usage:
            affected = q.execute('UPDATE users SET active = :active WHERE id = :id',
                                 active=True, id=1)
        """
        services = object.__getattribute__(self, '_services')
        db = services.get('db') or services.get('database')

        if db is None:
            raise QuantumBridgeError("Database service not available")

        if hasattr(db, 'execute'):
            result = db.execute(sql, params)
            if hasattr(result, 'rowcount'):
                return result.rowcount
            return result
        raise QuantumBridgeError("Database service doesn't support execute")

    # =========================================================================
    # HTTP Requests (q.http, q.get, q.post, etc.)
    # =========================================================================

    def http(self, url: str, method: str = 'GET', **kwargs) -> Any:
        """
        Make an HTTP request.

        Usage:
            response = q.http('https://api.example.com/data', method='POST', json={'key': 'value'})
        """
        try:
            import requests
        except ImportError:
            raise QuantumBridgeError("requests library not installed. Run: pip install requests")

        method = method.upper()
        response = requests.request(method, url, **kwargs)

        # Return a simple response object
        return HttpResponse(response)

    def get_http(self, url: str, **kwargs) -> Any:
        """GET request."""
        return self.http(url, 'GET', **kwargs)

    def post(self, url: str, **kwargs) -> Any:
        """POST request."""
        return self.http(url, 'POST', **kwargs)

    def put(self, url: str, **kwargs) -> Any:
        """PUT request."""
        return self.http(url, 'PUT', **kwargs)

    def delete(self, url: str, **kwargs) -> Any:
        """DELETE request."""
        return self.http(url, 'DELETE', **kwargs)

    def patch(self, url: str, **kwargs) -> Any:
        """PATCH request."""
        return self.http(url, 'PATCH', **kwargs)

    # =========================================================================
    # Message Queue (q.publish, q.send, q.dispatch)
    # =========================================================================

    def publish(self, topic: str, message: Any, headers: Optional[Dict] = None) -> None:
        """
        Publish a message to a topic.

        Usage:
            q.publish('orders.created', {'orderId': 123, 'total': 99.99})
        """
        services = object.__getattribute__(self, '_services')
        broker = services.get('broker') or services.get('message_broker')

        if broker is None:
            raise QuantumBridgeError("Message broker not available")

        from runtime.message_broker import Message
        msg = Message(body=message, headers=headers or {})
        broker.publish(topic, msg)

    def send(self, queue: str, message: Any, headers: Optional[Dict] = None) -> None:
        """
        Send a message to a queue.

        Usage:
            q.send('email-queue', {'to': 'user@example.com', 'subject': 'Welcome'})
        """
        services = object.__getattribute__(self, '_services')
        broker = services.get('broker') or services.get('message_broker')

        if broker is None:
            raise QuantumBridgeError("Message broker not available")

        from runtime.message_broker import Message
        msg = Message(body=message, headers=headers or {})
        broker.send(queue, msg)

    def dispatch(self, job_name: str, delay: Optional[str] = None, **params) -> int:
        """
        Dispatch a job to the job queue.

        Usage:
            job_id = q.dispatch('process-order', order_id=123)
            job_id = q.dispatch('send-reminder', delay='1h', user_id=456)
        """
        services = object.__getattribute__(self, '_services')
        jobs = services.get('jobs') or services.get('job_queue')

        if jobs is None:
            raise QuantumBridgeError("Job queue service not available")

        if hasattr(jobs, 'dispatch'):
            return jobs.dispatch(name=job_name, params=params, delay=delay)
        raise QuantumBridgeError("Job queue doesn't support dispatch")

    def schedule(self, job_name: str, cron: Optional[str] = None,
                 interval: Optional[str] = None, **params) -> str:
        """
        Schedule a recurring job.

        Usage:
            q.schedule('daily-report', cron='0 8 * * *')
            q.schedule('cleanup', interval='1h')
        """
        services = object.__getattribute__(self, '_services')
        scheduler = services.get('scheduler') or services.get('schedule')

        if scheduler is None:
            raise QuantumBridgeError("Scheduler service not available")

        if hasattr(scheduler, 'add_schedule'):
            return scheduler.add_schedule(job_name, cron=cron, interval=interval, **params)
        raise QuantumBridgeError("Scheduler doesn't support scheduling")

    # =========================================================================
    # Cache (q.cache)
    # =========================================================================

    def cache(self, key: str, value: Any = None, ttl: Optional[Union[int, str]] = None) -> Any:
        """
        Get or set cache value.

        Usage:
            # Get
            cached = q.cache('user:123')

            # Set with TTL
            q.cache('user:123', user_data, ttl='5m')
        """
        services = object.__getattribute__(self, '_services')
        cache_service = services.get('cache')

        if cache_service is None:
            # Use simple in-memory cache
            if not hasattr(self._local, 'cache'):
                self._local.cache = {}

            if value is None:
                return self._local.cache.get(key)
            else:
                self._local.cache[key] = value
                return value

        if value is None:
            return cache_service.get(key)
        else:
            return cache_service.set(key, value, ttl=ttl)

    def cache_delete(self, key: str) -> bool:
        """Delete a cache entry."""
        services = object.__getattribute__(self, '_services')
        cache_service = services.get('cache')

        if cache_service is None:
            if hasattr(self._local, 'cache'):
                return self._local.cache.pop(key, None) is not None
            return False

        return cache_service.delete(key)

    # =========================================================================
    # Session (q.session)
    # =========================================================================

    def session(self, key: str, value: Any = None) -> Any:
        """
        Get or set session value.

        Usage:
            # Get
            user_id = q.session('user_id')

            # Set
            q.session('cart', cart_items)
        """
        services = object.__getattribute__(self, '_services')
        session_service = services.get('session')

        if session_service is None:
            context = object.__getattribute__(self, '_context')
            if hasattr(context, 'session'):
                session_service = context.session
            else:
                raise QuantumBridgeError("Session service not available")

        if value is None:
            return session_service.get(key) if hasattr(session_service, 'get') else session_service[key]
        else:
            if hasattr(session_service, 'set'):
                session_service.set(key, value)
            else:
                session_service[key] = value

    # =========================================================================
    # Logging (q.log, q.info, q.warn, q.error, q.debug)
    # =========================================================================

    def log(self, message: str, level: str = 'info', **extra) -> None:
        """
        Log a message.

        Usage:
            q.log('Processing order', level='info', order_id=123)
        """
        import logging
        logger = logging.getLogger('quantum.python')

        log_func = getattr(logger, level.lower(), logger.info)

        if extra:
            message = f"{message} | {extra}"

        log_func(message)

    def info(self, message: str, **extra) -> None:
        """Log info message."""
        self.log(message, 'info', **extra)

    def warn(self, message: str, **extra) -> None:
        """Log warning message."""
        self.log(message, 'warning', **extra)

    def warning(self, message: str, **extra) -> None:
        """Log warning message (alias)."""
        self.log(message, 'warning', **extra)

    def error(self, message: str, **extra) -> None:
        """Log error message."""
        self.log(message, 'error', **extra)

    def debug(self, message: str, **extra) -> None:
        """Log debug message."""
        self.log(message, 'debug', **extra)

    # =========================================================================
    # Request Access (q.form, q.request, q.files)
    # =========================================================================

    @property
    def form(self) -> Dict[str, Any]:
        """
        Access form data from the request.

        Usage:
            email = q.form['email']
            password = q.form.get('password')
        """
        request = object.__getattribute__(self, '_request')
        if request is None:
            context = object.__getattribute__(self, '_context')
            if hasattr(context, 'form'):
                return context.form
            return {}

        if hasattr(request, 'form'):
            return dict(request.form)
        return {}

    @property
    def request(self) -> Any:
        """
        Access the full request object.

        Usage:
            method = q.request.method
            headers = q.request.headers
        """
        request = object.__getattribute__(self, '_request')
        if request is None:
            context = object.__getattribute__(self, '_context')
            if hasattr(context, 'request'):
                return context.request
        return request

    @property
    def files(self) -> Dict[str, Any]:
        """
        Access uploaded files.

        Usage:
            avatar = q.files['avatar']
        """
        request = object.__getattribute__(self, '_request')
        if request and hasattr(request, 'files'):
            return dict(request.files)
        return {}

    # =========================================================================
    # Control Flow (q.redirect, q.abort)
    # =========================================================================

    def redirect(self, url: str, status: int = 302) -> None:
        """
        Redirect to a URL.

        Usage:
            q.redirect('/dashboard')
            q.redirect('/login', status=301)
        """
        raise RedirectException(url, status)

    def abort(self, status: int, message: Optional[str] = None) -> None:
        """
        Abort request with error.

        Usage:
            q.abort(404, 'User not found')
            q.abort(403)
        """
        raise AbortException(status, message)

    # =========================================================================
    # Events (q.emit, q.on)
    # =========================================================================

    def emit(self, event: str, data: Any = None) -> None:
        """
        Emit an event.

        Usage:
            q.emit('user:registered', user_data)
        """
        services = object.__getattribute__(self, '_services')
        events = services.get('events')

        if events and hasattr(events, 'emit'):
            events.emit(event, data)
        else:
            # Fallback to publish if no event service
            self.publish(event.replace(':', '.'), data)

    def on(self, event: str, handler: Callable) -> None:
        """
        Register an event handler.

        Usage:
            def on_user_created(user):
                send_welcome_email(user)

            q.on('user:created', on_user_created)
        """
        services = object.__getattribute__(self, '_services')
        events = services.get('events')

        if events and hasattr(events, 'on'):
            events.on(event, handler)
        else:
            raise QuantumBridgeError("Event service not available")

    # =========================================================================
    # Utilities (q.render, q.json, q.now, etc.)
    # =========================================================================

    def render(self, template: str, **context) -> str:
        """
        Render a template.

        Usage:
            html = q.render('email/welcome.html', user=user)
        """
        services = object.__getattribute__(self, '_services')
        renderer = services.get('renderer') or services.get('template')

        if renderer and hasattr(renderer, 'render'):
            return renderer.render(template, context)

        # Simple string formatting fallback
        return template.format(**context)

    def json(self, data: Any) -> str:
        """Convert to JSON string."""
        return json.dumps(data, default=str)

    def parse_json(self, json_str: str) -> Any:
        """Parse JSON string."""
        return json.loads(json_str)

    def now(self) -> 'datetime':
        """Get current datetime."""
        from datetime import datetime
        return datetime.now()

    def today(self) -> 'date':
        """Get current date."""
        from datetime import date
        return date.today()

    def uuid(self) -> str:
        """Generate a UUID."""
        import uuid
        return str(uuid.uuid4())

    def sleep(self, seconds: float) -> None:
        """Sleep for specified seconds."""
        time.sleep(seconds)

    # =========================================================================
    # Convenience methods
    # =========================================================================

    def __contains__(self, name: str) -> bool:
        """Check if variable exists."""
        try:
            self.__getattr__(name)
            return True
        except AttributeError:
            return False

    def __repr__(self) -> str:
        return "<QuantumBridge>"


@dataclass
class HttpResponse:
    """Simple HTTP response wrapper."""

    _response: Any

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def ok(self) -> bool:
        return self._response.ok

    @property
    def text(self) -> str:
        return self._response.text

    @property
    def content(self) -> bytes:
        return self._response.content

    @property
    def headers(self) -> Dict[str, str]:
        return dict(self._response.headers)

    def json(self) -> Any:
        return self._response.json()

    def raise_for_status(self) -> None:
        self._response.raise_for_status()


class RedirectException(Exception):
    """Raised to trigger a redirect."""

    def __init__(self, url: str, status: int = 302):
        self.url = url
        self.status = status
        super().__init__(f"Redirect to {url}")


class AbortException(Exception):
    """Raised to abort the request."""

    def __init__(self, status: int, message: Optional[str] = None):
        self.status = status
        self.message = message or f"HTTP {status}"
        super().__init__(self.message)
