"""
Quantum Runtime for Python
==========================

Runtime support library for transpiled Quantum code.
Generated Python code imports this module for common utilities.
"""

from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
import html as html_module
import json
import re


# =============================================================================
# HTML Utilities
# =============================================================================

def escape(value: Any) -> str:
    """
    Escape HTML entities in a value.

    Args:
        value: Value to escape

    Returns:
        HTML-escaped string
    """
    if value is None:
        return ''
    return html_module.escape(str(value))


def raw(value: Any) -> 'RawHTML':
    """
    Mark a value as raw HTML (no escaping).

    Args:
        value: HTML string

    Returns:
        RawHTML wrapper
    """
    return RawHTML(value)


class RawHTML:
    """Wrapper for raw HTML that should not be escaped."""

    def __init__(self, content: Any):
        self.content = str(content) if content is not None else ''

    def __str__(self) -> str:
        return self.content

    def __repr__(self) -> str:
        return f'RawHTML({self.content!r})'


# =============================================================================
# Databinding
# =============================================================================

def bind(template: str, context: Dict[str, Any]) -> str:
    """
    Apply databinding to a template string.

    Args:
        template: Template with {expression} placeholders
        context: Variable context

    Returns:
        Resolved string
    """
    def replace(match):
        expr = match.group(1).strip()
        try:
            # Evaluate expression in context
            result = eval(expr, {'__builtins__': {}}, context)
            return escape(result) if not isinstance(result, RawHTML) else str(result)
        except Exception:
            return match.group(0)

    return re.sub(r'\{([^}]+)\}', replace, template)


# =============================================================================
# Component Base
# =============================================================================

class Component:
    """
    Base class for Quantum components.

    Generated component classes inherit from this.
    """

    def __init__(self, **props):
        """
        Initialize component with props.

        Args:
            **props: Component properties
        """
        self.props = props
        self._html: List[str] = []
        self._context: Dict[str, Any] = {}

    def render(self) -> str:
        """
        Render the component.

        Override in generated subclasses.

        Returns:
            HTML string
        """
        raise NotImplementedError("Component.render() must be implemented")

    def __str__(self) -> str:
        """String representation returns rendered HTML."""
        return self.render()

    def __html__(self) -> str:
        """Jinja2/Flask compatible HTML method."""
        return self.render()


# =============================================================================
# Flash Messages
# =============================================================================

_flash_messages: List[Dict[str, str]] = []


def flash(message: str, category: str = 'info'):
    """
    Add a flash message.

    Args:
        message: The message text
        category: Message category (info, success, warning, error)
    """
    _flash_messages.append({
        'message': message,
        'category': category
    })


def get_flashed_messages(with_categories: bool = False) -> Union[List[str], List[Dict[str, str]]]:
    """
    Get and clear flash messages.

    Args:
        with_categories: Include category with each message

    Returns:
        List of messages or dicts with message/category
    """
    global _flash_messages
    messages = _flash_messages.copy()
    _flash_messages = []

    if with_categories:
        return messages
    return [m['message'] for m in messages]


# =============================================================================
# Session & Application Scope
# =============================================================================

class ScopeDict(dict):
    """Dictionary with attribute access for session/application scope."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any):
        self[name] = value

    def __delattr__(self, name: str):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")


# Global session and application scopes
session = ScopeDict()
application = ScopeDict()


# =============================================================================
# Database Utilities
# =============================================================================

class Database:
    """
    Simple database wrapper.

    For actual database access, integrate with SQLAlchemy or similar.
    """

    _connections: Dict[str, Any] = {}

    @classmethod
    def get_connection(cls, name: str = 'default') -> 'Database':
        """Get or create a database connection."""
        if name not in cls._connections:
            cls._connections[name] = cls(name)
        return cls._connections[name]

    def __init__(self, name: str):
        self.name = name
        self._conn = None

    def execute(self, sql: str, params: List[Any] = None):
        """
        Execute a SQL query.

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            Query result
        """
        # This is a placeholder - actual implementation depends on database
        raise NotImplementedError("Database.execute() requires database configuration")


# =============================================================================
# Request Context (Flask Integration)
# =============================================================================

class RequestContext:
    """
    Request context for web applications.

    In Flask apps, this wraps flask.request.
    """

    def __init__(self):
        self._form: Dict[str, Any] = {}
        self._args: Dict[str, Any] = {}
        self._cookies: Dict[str, str] = {}
        self._headers: Dict[str, str] = {}
        self._method: str = 'GET'
        self._path: str = '/'

    @property
    def form(self) -> Dict[str, Any]:
        """Form data from POST request."""
        try:
            from flask import request as flask_request
            return flask_request.form
        except (ImportError, RuntimeError):
            return self._form

    @property
    def args(self) -> Dict[str, Any]:
        """Query string parameters."""
        try:
            from flask import request as flask_request
            return flask_request.args
        except (ImportError, RuntimeError):
            return self._args

    @property
    def method(self) -> str:
        """HTTP method."""
        try:
            from flask import request as flask_request
            return flask_request.method
        except (ImportError, RuntimeError):
            return self._method

    @property
    def path(self) -> str:
        """Request path."""
        try:
            from flask import request as flask_request
            return flask_request.path
        except (ImportError, RuntimeError):
            return self._path


# Global request context
request = RequestContext()


# =============================================================================
# Redirect
# =============================================================================

def redirect(url: str, code: int = 302):
    """
    Redirect to a URL.

    Args:
        url: Target URL
        code: HTTP status code (302 = temporary, 301 = permanent)

    Returns:
        Redirect response
    """
    try:
        from flask import redirect as flask_redirect
        return flask_redirect(url, code=code)
    except ImportError:
        # Fallback for non-Flask usage
        return f'<meta http-equiv="refresh" content="0; url={url}">'


# =============================================================================
# Utilities
# =============================================================================

def to_json(value: Any) -> str:
    """Convert value to JSON string."""
    return json.dumps(value)


def from_json(value: str) -> Any:
    """Parse JSON string."""
    return json.loads(value)


def safe_get(obj: Any, *keys, default: Any = None) -> Any:
    """
    Safely get nested values.

    Args:
        obj: Object to get value from
        *keys: Keys/indices to traverse
        default: Default value if not found

    Returns:
        Value or default
    """
    current = obj
    for key in keys:
        try:
            if isinstance(current, dict):
                current = current[key]
            elif isinstance(current, (list, tuple)):
                current = current[int(key)]
            else:
                current = getattr(current, key)
        except (KeyError, IndexError, AttributeError, TypeError, ValueError):
            return default
    return current


# =============================================================================
# Data Loading (Phase 2)
# =============================================================================

def load_data(source: str, type: str = 'json') -> Any:
    """
    Load data from a file or URL.

    Args:
        source: File path or URL
        type: Data type (json, csv, xml)

    Returns:
        Parsed data
    """
    import os

    # Check if URL
    if source.startswith(('http://', 'https://')):
        try:
            import urllib.request
            with urllib.request.urlopen(source) as response:
                content = response.read().decode('utf-8')
        except Exception as e:
            raise RuntimeError(f"Failed to fetch {source}: {e}")
    else:
        # File path
        if not os.path.exists(source):
            raise FileNotFoundError(f"Data file not found: {source}")
        with open(source, 'r', encoding='utf-8') as f:
            content = f.read()

    # Parse based on type
    if type == 'json':
        return json.loads(content)
    elif type == 'csv':
        import csv
        import io
        reader = csv.DictReader(io.StringIO(content))
        return list(reader)
    elif type == 'xml':
        import xml.etree.ElementTree as ET
        return ET.fromstring(content)
    else:
        return content


# =============================================================================
# HTTP Invocation (Phase 2)
# =============================================================================

def invoke(url: str, method: str = 'GET', headers: Dict[str, str] = None,
           body: Any = None, timeout: int = 30) -> Any:
    """
    Make an HTTP request.

    Args:
        url: Target URL
        method: HTTP method
        headers: Request headers
        body: Request body (will be JSON-encoded)
        timeout: Timeout in seconds

    Returns:
        Response data (JSON-parsed if applicable)
    """
    import urllib.request
    import urllib.error

    headers = headers or {}

    # Add JSON content type if body provided
    if body is not None and 'Content-Type' not in headers:
        headers['Content-Type'] = 'application/json'

    # Encode body
    data = None
    if body is not None:
        data = json.dumps(body).encode('utf-8')

    # Create request
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read().decode('utf-8')
            content_type = response.headers.get('Content-Type', '')

            # Parse JSON if applicable
            if 'application/json' in content_type:
                return json.loads(content)
            return content
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Request failed: {e.reason}")


# =============================================================================
# File Handling (Phase 2)
# =============================================================================

def handle_file(file: Any, action: str = 'upload', destination: str = './uploads/') -> Dict[str, Any]:
    """
    Handle file operations.

    Args:
        file: File object or path
        action: Action type (upload, read, delete)
        destination: Destination directory for uploads

    Returns:
        Result dict with file info
    """
    import os
    import shutil
    import uuid

    result = {
        'success': False,
        'message': '',
        'path': None,
        'filename': None,
        'size': 0
    }

    try:
        if action == 'upload':
            # Ensure destination exists
            os.makedirs(destination, exist_ok=True)

            # Handle werkzeug FileStorage (Flask uploads)
            if hasattr(file, 'save') and hasattr(file, 'filename'):
                filename = file.filename
                # Generate unique name to avoid conflicts
                ext = os.path.splitext(filename)[1]
                unique_name = f"{uuid.uuid4().hex}{ext}"
                filepath = os.path.join(destination, unique_name)
                file.save(filepath)
                result['success'] = True
                result['path'] = filepath
                result['filename'] = unique_name
                result['original_name'] = filename
                result['size'] = os.path.getsize(filepath)
            elif isinstance(file, str) and os.path.exists(file):
                # Copy existing file
                filename = os.path.basename(file)
                filepath = os.path.join(destination, filename)
                shutil.copy2(file, filepath)
                result['success'] = True
                result['path'] = filepath
                result['filename'] = filename
                result['size'] = os.path.getsize(filepath)
            else:
                result['message'] = 'Invalid file input'

        elif action == 'read':
            if isinstance(file, str) and os.path.exists(file):
                with open(file, 'rb') as f:
                    result['content'] = f.read()
                    result['success'] = True
                    result['size'] = len(result['content'])
            else:
                result['message'] = 'File not found'

        elif action == 'delete':
            if isinstance(file, str) and os.path.exists(file):
                os.remove(file)
                result['success'] = True
                result['message'] = 'File deleted'
            else:
                result['message'] = 'File not found'

    except Exception as e:
        result['message'] = str(e)

    return result


# =============================================================================
# Email Sending (Phase 2)
# =============================================================================

def send_mail(to: str, from_addr: str = None, subject: str = '',
              body: str = '', html: bool = False, attachments: List[str] = None) -> bool:
    """
    Send an email.

    Args:
        to: Recipient email address(es)
        from_addr: Sender email address
        subject: Email subject
        body: Email body
        html: Whether body is HTML
        attachments: List of file paths to attach

    Returns:
        True if sent successfully
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email import encoders
    import os

    # Get SMTP configuration from environment
    smtp_host = os.environ.get('SMTP_HOST', 'localhost')
    smtp_port = int(os.environ.get('SMTP_PORT', '25'))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    smtp_ssl = os.environ.get('SMTP_SSL', 'false').lower() == 'true'

    if not from_addr:
        from_addr = os.environ.get('SMTP_FROM', 'noreply@localhost')

    # Create message
    if attachments:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, 'html' if html else 'plain'))
    else:
        msg = MIMEText(body, 'html' if html else 'plain')

    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to if isinstance(to, str) else ', '.join(to)

    # Add attachments
    if attachments:
        for filepath in attachments:
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(filepath)}"')
                    msg.attach(part)

    try:
        if smtp_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)

        if smtp_user and smtp_pass:
            server.login(smtp_user, smtp_pass)

        recipients = [to] if isinstance(to, str) else list(to)
        server.sendmail(from_addr, recipients, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False


# =============================================================================
# Job Queue (Phase 3)
# =============================================================================

class JobQueue:
    """Simple job queue for background processing."""

    _jobs: Dict[str, Callable] = {}
    _pending: List[Dict[str, Any]] = []

    @classmethod
    def task(cls, queue: str = 'default', priority: int = 0):
        """Decorator to register a job task."""
        def decorator(func: Callable):
            cls._jobs[func.__name__] = {
                'func': func,
                'queue': queue,
                'priority': priority
            }
            return func
        return decorator

    @classmethod
    def dispatch(cls, name: str, delay: str = None, **params):
        """Dispatch a job for execution."""
        import threading

        if name not in cls._jobs:
            raise ValueError(f"Job not found: {name}")

        job = cls._jobs[name]

        def run_job():
            if delay:
                import time
                # Parse delay (e.g., "5m", "1h", "30s")
                seconds = cls._parse_delay(delay)
                time.sleep(seconds)
            job['func'](**params)

        thread = threading.Thread(target=run_job, daemon=True)
        thread.start()

    @classmethod
    def cancel(cls, name: str):
        """Cancel pending jobs (best effort)."""
        cls._pending = [j for j in cls._pending if j.get('name') != name]

    @staticmethod
    def _parse_delay(delay: str) -> float:
        """Parse delay string to seconds."""
        import re
        match = re.match(r'(\d+)([smhd])', delay)
        if not match:
            return 0
        value, unit = int(match.group(1)), match.group(2)
        multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        return value * multipliers.get(unit, 1)


# =============================================================================
# Scheduler (Phase 3)
# =============================================================================

class Scheduler:
    """Task scheduler for periodic and one-time tasks."""

    _tasks: Dict[str, Dict[str, Any]] = {}
    _running: bool = False

    @classmethod
    def schedule(cls, interval: str = None, cron: str = None, at: str = None, enabled: bool = True):
        """Decorator to schedule a task."""
        def decorator(func: Callable):
            cls._tasks[func.__name__] = {
                'func': func,
                'interval': interval,
                'cron': cron,
                'at': at,
                'enabled': enabled
            }
            return func
        return decorator

    @classmethod
    def start(cls):
        """Start the scheduler."""
        import threading

        if cls._running:
            return

        cls._running = True

        def scheduler_loop():
            import time
            while cls._running:
                for name, task in cls._tasks.items():
                    if not task['enabled']:
                        continue
                    # Simple interval handling
                    if task.get('interval'):
                        # Would need proper timing logic
                        pass
                time.sleep(1)

        thread = threading.Thread(target=scheduler_loop, daemon=True)
        thread.start()

    @classmethod
    def stop(cls):
        """Stop the scheduler."""
        cls._running = False


# =============================================================================
# Async Thread (Phase 3)
# =============================================================================

class AsyncThread:
    """Wrapper for async thread execution."""

    _threads: Dict[str, 'AsyncThread'] = {}

    def __init__(self, name: str, target: Callable, timeout: str = None, on_complete: Callable = None):
        self.name = name
        self.target = target
        self.timeout = timeout
        self.on_complete = on_complete
        self._thread = None
        self._result = None
        AsyncThread._threads[name] = self

    def start(self):
        """Start the thread."""
        import threading

        def wrapper():
            try:
                self._result = self.target()
                if self.on_complete:
                    self.on_complete(self._result)
            except Exception as e:
                self._result = e

        self._thread = threading.Thread(target=wrapper, daemon=True)
        self._thread.start()

    def join(self, timeout: float = None):
        """Wait for thread completion."""
        if self._thread:
            timeout_seconds = None
            if timeout:
                timeout_seconds = float(timeout)
            elif self.timeout:
                timeout_seconds = JobQueue._parse_delay(self.timeout)
            self._thread.join(timeout=timeout_seconds)

    def terminate(self):
        """Terminate the thread (best effort)."""
        # Python threads can't be forcefully terminated
        # This is a placeholder for cooperative termination
        pass

    @property
    def result(self):
        """Get thread result."""
        return self._result


def parallel_execute(tasks: List[Callable], max_workers: int = 4) -> List[Any]:
    """Execute tasks in parallel."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(task): idx for idx, task in enumerate(tasks)}
        results = [None] * len(tasks)
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                results[idx] = e
    return results


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # HTML
    'escape',
    'raw',
    'RawHTML',
    'bind',

    # Component
    'Component',

    # Flash
    'flash',
    'get_flashed_messages',

    # Scope
    'session',
    'application',
    'ScopeDict',

    # Database
    'Database',

    # Request
    'request',
    'RequestContext',
    'redirect',

    # Data (Phase 2)
    'load_data',
    'invoke',
    'handle_file',
    'send_mail',

    # Async (Phase 3)
    'JobQueue',
    'Scheduler',
    'AsyncThread',
    'parallel_execute',

    # Utilities
    'to_json',
    'from_json',
    'safe_get',
]
