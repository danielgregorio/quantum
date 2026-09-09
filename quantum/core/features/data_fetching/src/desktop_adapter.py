"""
Data Fetching Feature - Desktop Adapter
Generates Python code using requests library for the Desktop (pywebview) target.
"""

import json
from typing import Dict, Any, Optional
from .ast_node import FetchNode


class FetchDesktopAdapter:
    """Generates Python code for q:fetch nodes in desktop applications."""

    def __init__(self):
        self._fetch_counter = 0
        self._fetches: Dict[str, FetchNode] = {}

    def register_fetch(self, node: FetchNode) -> str:
        """
        Register a FetchNode and return its unique ID.

        Args:
            node: FetchNode to register

        Returns:
            Unique fetch ID
        """
        self._fetch_counter += 1
        fetch_id = f"fetch_{self._fetch_counter}"
        self._fetches[fetch_id] = node
        return fetch_id

    def generate_fetch_class(self) -> str:
        """
        Generate the QuantumFetch class for handling fetch requests.

        Returns:
            Python code for the fetch management class
        """
        return QUANTUM_FETCH_CLASS

    def generate_fetch_methods(self) -> str:
        """
        Generate Python methods for each registered fetch.

        Returns:
            Python code with fetch methods
        """
        if not self._fetches:
            return '    # No fetch nodes defined'

        methods = []
        for fetch_id, node in self._fetches.items():
            method = self._generate_fetch_method(fetch_id, node)
            methods.append(method)

        return '\n\n'.join(methods)

    def _generate_fetch_method(self, fetch_id: str, node: FetchNode) -> str:
        """
        Generate a Python method for a specific fetch.

        Args:
            fetch_id: Unique fetch identifier
            node: FetchNode to generate code for

        Returns:
            Python method code
        """
        # Build headers dict
        headers_dict = {}
        for header in node.headers:
            headers_dict[header.name] = header.value

        # Escape URL and other strings
        url_escaped = node.url.replace("'", "\\'")

        lines = [
            f"    def {fetch_id}(self, params=None):",
            f'        """Fetch: {node.name} from {node.url[:50]}"""',
            f"        url = '{url_escaped}'",
            f"",
            f"        # Resolve URL parameters from state",
            f"        url = self._resolve_url(url, params)",
            f"",
        ]

        # Check cache first
        cache_seconds = node.get_cache_seconds()
        if cache_seconds and cache_seconds > 0:
            lines.extend([
                f"        # Check cache",
                f"        cache_key = f'{node.method}:{{url}}'",
                f"        cached = self._check_cache(cache_key, {cache_seconds})",
                f"        if cached is not None:",
                f"            self.state.set('{node.name}', cached)",
                f"            self.state.set('{node.name}_loading', False)",
                f"            self.state.set('{node.name}_error', None)",
                f"            return cached",
                f"",
            ])

        # Set loading state
        lines.extend([
            f"        # Set loading state",
            f"        self.state.set('{node.name}_loading', True)",
            f"        self.state.set('{node.name}_error', None)",
            f"",
        ])

        # Build request
        lines.extend([
            f"        try:",
            f"            headers = {repr(headers_dict)}",
            f"            headers['Content-Type'] = '{node.content_type}'",
            f"",
        ])

        # Add request body for non-GET methods
        if node.method.upper() in ['POST', 'PUT', 'PATCH']:
            if node.body:
                lines.extend([
                    f"            # Request body",
                    f"            body = self._resolve_value('{node.body}')",
                    f"            if isinstance(body, dict):",
                    f"                body = json.dumps(body)",
                    f"",
                ])
            else:
                lines.append(f"            body = None")

        # Execute request
        method_lower = node.method.lower()
        if node.method.upper() in ['POST', 'PUT', 'PATCH']:
            lines.extend([
                f"            response = requests.{method_lower}(",
                f"                url,",
                f"                headers=headers,",
                f"                data=body,",
                f"                timeout={node.timeout / 1000}",
                f"            )",
            ])
        else:
            lines.extend([
                f"            response = requests.{method_lower}(",
                f"                url,",
                f"                headers=headers,",
                f"                timeout={node.timeout / 1000}",
                f"            )",
            ])

        lines.extend([
            f"            response.raise_for_status()",
            f"",
        ])

        # Parse response
        if node.response_format == 'text':
            lines.append(f"            data = response.text")
        elif node.response_format == 'blob':
            lines.append(f"            data = response.content")
        else:
            lines.extend([
                f"            # Parse response",
                f"            content_type = response.headers.get('content-type', '')",
                f"            if 'application/json' in content_type:",
                f"                data = response.json()",
                f"            else:",
                f"                data = response.text",
            ])

        # Apply transform
        if node.transform:
            lines.extend([
                f"",
                f"            # Apply transform",
                f"            data = self._apply_transform(data, '{node.transform}')",
            ])

        # Cache result
        if cache_seconds and cache_seconds > 0:
            lines.extend([
                f"",
                f"            # Cache result",
                f"            self._set_cache(cache_key, data)",
            ])

        # Update state
        lines.extend([
            f"",
            f"            # Update state",
            f"            self.state.set('{node.name}', data)",
            f"            self.state.set('{node.name}_loading', False)",
            f"            self.state.set('{node.name}_error', None)",
            f"",
        ])

        # Call success callback
        if node.on_success:
            lines.extend([
                f"            # Success callback",
                f"            if hasattr(self.api, '{node.on_success}'):",
                f"                getattr(self.api, '{node.on_success}')(data)",
                f"",
            ])

        lines.append(f"            return data")

        # Error handling
        lines.extend([
            f"",
            f"        except requests.RequestException as e:",
            f"            error_msg = str(e)",
            f"            self.state.set('{node.name}_loading', False)",
            f"            self.state.set('{node.name}_error', error_msg)",
            f"            self.state.set('{node.name}', None)",
        ])

        # Call error callback
        if node.on_error:
            lines.extend([
                f"            # Error callback",
                f"            if hasattr(self.api, '{node.on_error}'):",
                f"                getattr(self.api, '{node.on_error}')(error_msg)",
            ])

        lines.extend([
            f"            return None",
        ])

        return '\n'.join(lines)

    def generate_initial_fetches(self) -> str:
        """
        Generate code to execute initial fetches on app start.

        Returns:
            Python code for initial fetch execution
        """
        if not self._fetches:
            return '        pass  # No initial fetches'

        lines = []
        for fetch_id, node in self._fetches.items():
            if not node.lazy:
                lines.append(f"        self.fetch.{fetch_id}()")

        return '\n'.join(lines) if lines else '        pass  # All fetches are lazy'


# Python class template for fetch management
QUANTUM_FETCH_CLASS = '''
import json
import threading
import time
from typing import Any, Dict, Optional
import requests


class QuantumFetch:
    """Manages fetch requests with caching and state updates."""

    def __init__(self, state, api=None):
        self.state = state
        self.api = api
        self._cache: Dict[str, tuple] = {}  # key -> (data, expires_at)
        self._polling_threads: Dict[str, threading.Event] = {}

    def _resolve_url(self, url: str, params: Optional[Dict] = None) -> str:
        """Resolve URL parameters from state and params dict."""
        import re

        def replace_param(match):
            var_name = match.group(1)
            # Check params first
            if params and var_name in params:
                return str(params[var_name])
            # Then check state
            value = self.state.get(var_name)
            return str(value) if value is not None else match.group(0)

        return re.sub(r'\\{([^}]+)\\}', replace_param, url)

    def _resolve_value(self, value_expr: str) -> Any:
        """Resolve a value expression from state."""
        if not value_expr:
            return None

        # Check if it's a state reference
        if value_expr.startswith('{') and value_expr.endswith('}'):
            var_name = value_expr[1:-1].strip()
            return self.state.get(var_name)

        return value_expr

    def _check_cache(self, key: str, ttl_seconds: int) -> Optional[Any]:
        """Check if cached data exists and is not expired."""
        if key in self._cache:
            data, expires_at = self._cache[key]
            if time.time() < expires_at:
                return data
            else:
                del self._cache[key]
        return None

    def _set_cache(self, key: str, data: Any, ttl_seconds: int = 300):
        """Cache data with expiration."""
        self._cache[key] = (data, time.time() + ttl_seconds)

    def _apply_transform(self, data: Any, transform_expr: str) -> Any:
        """Apply a transform expression to data."""
        # Simple transform support - can be extended
        if transform_expr.startswith('.'):
            # Property access like ".data" or ".results"
            for prop in transform_expr[1:].split('.'):
                if isinstance(data, dict) and prop in data:
                    data = data[prop]
                elif hasattr(data, prop):
                    data = getattr(data, prop)
        return data

    def start_polling(self, fetch_id: str, fetch_method, interval_ms: int):
        """Start polling a fetch at specified interval."""
        if fetch_id in self._polling_threads:
            self.stop_polling(fetch_id)

        stop_event = threading.Event()
        self._polling_threads[fetch_id] = stop_event

        def poll():
            while not stop_event.is_set():
                try:
                    fetch_method()
                except Exception:
                    pass
                stop_event.wait(interval_ms / 1000)

        thread = threading.Thread(target=poll, daemon=True)
        thread.start()

    def stop_polling(self, fetch_id: str):
        """Stop polling for a specific fetch."""
        if fetch_id in self._polling_threads:
            self._polling_threads[fetch_id].set()
            del self._polling_threads[fetch_id]

    def stop_all_polling(self):
        """Stop all polling threads."""
        for fetch_id in list(self._polling_threads.keys()):
            self.stop_polling(fetch_id)
'''
