"""
Data Fetching Feature - AST Nodes
Defines FetchNode and related nodes for q:fetch declarative data fetching
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from core.ast_nodes import QuantumNode


@dataclass
class FetchHeaderNode(QuantumNode):
    """Represents a <q:header> within q:fetch for HTTP headers."""

    name: str
    value: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "fetch_header",
            "name": self.name,
            "value": self.value[:50] + "..." if len(str(self.value)) > 50 else self.value
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Fetch header name is required")
        if self.value is None:
            errors.append(f"Fetch header '{self.name}' value is required")
        return errors


@dataclass
class FetchLoadingNode(QuantumNode):
    """Represents <q:loading> within q:fetch - content shown during loading."""

    children: List[QuantumNode] = field(default_factory=list)

    def add_child(self, child: QuantumNode):
        """Add a child node to loading content."""
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "fetch_loading",
            "children_count": len(self.children)
        }

    def validate(self) -> List[str]:
        errors = []
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


@dataclass
class FetchErrorNode(QuantumNode):
    """Represents <q:error> within q:fetch - content shown on error."""

    children: List[QuantumNode] = field(default_factory=list)

    def add_child(self, child: QuantumNode):
        """Add a child node to error content."""
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "fetch_error",
            "children_count": len(self.children)
        }

    def validate(self) -> List[str]:
        errors = []
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


@dataclass
class FetchSuccessNode(QuantumNode):
    """Represents <q:success> within q:fetch - content shown on success."""

    children: List[QuantumNode] = field(default_factory=list)

    def add_child(self, child: QuantumNode):
        """Add a child node to success content."""
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "fetch_success",
            "children_count": len(self.children)
        }

    def validate(self) -> List[str]:
        errors = []
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class FetchNode(QuantumNode):
    """
    Represents a <q:fetch> - Declarative data fetching with state management.

    Examples:
      <q:fetch name="users" url="/api/users" method="GET" cache="5m">
          <q:loading><ui:skeleton /></q:loading>
          <q:error><ui:alert variant="danger">{error}</ui:alert></q:error>
          <q:success>
              <ui:list source="{users}" />
          </q:success>
      </q:fetch>

      <q:fetch name="user" url="/api/users/{userId}" method="GET">
          <q:header name="Authorization" value="Bearer {token}" />
          <q:success>
              <div>Name: {user.name}</div>
          </q:success>
      </q:fetch>

      <q:fetch name="orders" url="/api/orders" method="POST" body="{orderData}">
          <q:loading>Creating order...</q:loading>
          <q:error>Failed: {error}</q:error>
          <q:success>Order created: {orders.id}</q:success>
      </q:fetch>
    """

    def __init__(self, name: str, url: str):
        self.name = name  # Variable name for result data
        self.url = url    # Fetch URL (supports databinding)

        # HTTP configuration
        self.method = "GET"  # GET, POST, PUT, DELETE, PATCH
        self.headers: List[FetchHeaderNode] = []
        self.body = None     # Request body (JSON string or databinding)
        self.content_type = "application/json"

        # Caching
        self.cache = None    # Cache TTL (e.g., "5m", "1h", "30s", "0" for no cache)
        self.cache_key = None  # Custom cache key (default: url + method)

        # Polling / Refetch
        self.interval = None  # Polling interval (e.g., "10s", "1m")
        self.refetch_on = None  # Events that trigger refetch

        # Request configuration
        self.timeout = 30000  # Timeout in ms (default 30s)
        self.retry = 0        # Number of retries on failure
        self.retry_delay = 1000  # Delay between retries in ms

        # Response handling
        self.transform = None  # Transform expression for response
        self.response_format = "auto"  # auto, json, text, blob

        # Callbacks
        self.on_success = None  # Function to call on success
        self.on_error = None    # Function to call on error

        # State children (loading/error/success)
        self.loading_node: Optional[FetchLoadingNode] = None
        self.error_node: Optional[FetchErrorNode] = None
        self.success_node: Optional[FetchSuccessNode] = None

        # Fallback content (if no q:loading/error/success provided)
        self.fallback_children: List[QuantumNode] = []

        # Abort on unmount (for SPA/reactive)
        self.abort_on_unmount = True

        # Lazy loading (don't fetch until visible)
        self.lazy = False

        # Credentials mode (for cookies)
        self.credentials = None  # "same-origin", "include", "omit"

    def add_header(self, header: FetchHeaderNode):
        """Add HTTP header to the fetch request."""
        self.headers.append(header)

    def set_loading(self, node: FetchLoadingNode):
        """Set the loading state content."""
        self.loading_node = node

    def set_error(self, node: FetchErrorNode):
        """Set the error state content."""
        self.error_node = node

    def set_success(self, node: FetchSuccessNode):
        """Set the success state content."""
        self.success_node = node

    def add_fallback_child(self, child: QuantumNode):
        """Add fallback content for simple fetch without states."""
        self.fallback_children.append(child)

    def get_cache_seconds(self) -> Optional[int]:
        """Parse cache TTL string to seconds. Returns None if no caching."""
        if not self.cache:
            return None

        cache = self.cache.strip().lower()

        if cache == "0" or cache == "false" or cache == "no":
            return 0

        # Parse duration string (e.g., "5m", "1h", "30s")
        import re
        match = re.match(r'^(\d+)(s|m|h|d)?$', cache)
        if match:
            value = int(match.group(1))
            unit = match.group(2) or 's'

            multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
            return value * multipliers.get(unit, 1)

        # If it's just a number, treat as seconds
        try:
            return int(cache)
        except ValueError:
            return None

    def get_interval_ms(self) -> Optional[int]:
        """Parse interval string to milliseconds. Returns None if no polling."""
        if not self.interval:
            return None

        interval = self.interval.strip().lower()

        # Parse duration string (e.g., "10s", "1m", "500ms")
        import re
        match = re.match(r'^(\d+)(ms|s|m)?$', interval)
        if match:
            value = int(match.group(1))
            unit = match.group(2) or 'ms'

            multipliers = {'ms': 1, 's': 1000, 'm': 60000}
            return value * multipliers.get(unit, 1)

        # If it's just a number, treat as milliseconds
        try:
            return int(interval)
        except ValueError:
            return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "fetch",
            "name": self.name,
            "url": self.url[:50] + "..." if len(self.url) > 50 else self.url,
            "method": self.method,
            "headers_count": len(self.headers),
            "cache": self.cache,
            "interval": self.interval,
            "timeout": self.timeout,
            "retry": self.retry,
            "transform": self.transform,
            "has_loading": self.loading_node is not None,
            "has_error": self.error_node is not None,
            "has_success": self.success_node is not None,
            "on_success": self.on_success,
            "on_error": self.on_error,
        }

    def validate(self) -> List[str]:
        errors = []

        if not self.name:
            errors.append("Fetch name is required")

        if not self.url:
            errors.append("Fetch URL is required")

        # Validate HTTP method
        valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        if self.method.upper() not in valid_methods:
            errors.append(f"Invalid HTTP method: {self.method}. Must be one of {valid_methods}")

        # Validate headers
        for header in self.headers:
            errors.extend(header.validate())

        # Validate state nodes
        if self.loading_node:
            errors.extend(self.loading_node.validate())
        if self.error_node:
            errors.extend(self.error_node.validate())
        if self.success_node:
            errors.extend(self.success_node.validate())

        # Validate fallback children
        for child in self.fallback_children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())

        # Validate response format
        valid_formats = ['auto', 'json', 'text', 'blob']
        if self.response_format not in valid_formats:
            errors.append(f"Invalid response format: {self.response_format}. Must be one of {valid_formats}")

        # Validate credentials mode
        if self.credentials and self.credentials not in ['same-origin', 'include', 'omit']:
            errors.append(f"Invalid credentials mode: {self.credentials}. Must be same-origin, include, or omit")

        return errors

    def __repr__(self):
        return f'<FetchNode name={self.name} url={self.url[:30]}... method={self.method}>'
