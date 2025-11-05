"""
Invocation Feature - AST Nodes
Defines InvokeNode and InvokeHeaderNode for q:invoke
"""

from typing import List, Dict, Any
from core.ast_nodes import QuantumNode, QuantumParam


class InvokeNode(QuantumNode):
    """Represents a <q:invoke> - Universal invocation for functions, components, HTTP, etc."""

    def __init__(self, name: str):
        self.name = name  # Variable name for result

        # Invocation target (determines type)
        self.function = None      # Local function name
        self.component = None     # Local component name
        self.url = None          # HTTP/REST endpoint
        self.endpoint = None     # GraphQL/SOAP endpoint
        self.service = None      # Service name (for service discovery)

        # HTTP-specific
        self.method = "GET"      # GET, POST, PUT, DELETE, PATCH
        self.headers: List['InvokeHeaderNode'] = []
        self.body = None         # Request body (for POST/PUT/PATCH)
        self.content_type = "application/json"

        # Authentication
        self.auth_type = None    # bearer, apikey, basic, oauth2
        self.auth_token = None   # Bearer token or API key
        self.auth_header = None  # Header name for API key (default: Authorization)
        self.auth_username = None  # Basic auth username
        self.auth_password = None  # Basic auth password

        # Parameters (query params for HTTP, args for functions/components)
        self.params: List[QuantumParam] = []

        # Timeouts and retries
        self.timeout = 30000     # Default 30s
        self.retry = 0           # Number of retries
        self.retry_delay = 1000  # Delay between retries in ms

        # Response handling
        self.response_format = "auto"  # auto, json, text, xml, binary
        self.transform = None    # Transformation expression
        self.cache = False
        self.ttl = None
        self.result = None       # Variable name for metadata

    def add_header(self, header: 'InvokeHeaderNode'):
        """Add HTTP header"""
        self.headers.append(header)

    def add_param(self, param: QuantumParam):
        """Add parameter"""
        self.params.append(param)

    def get_invocation_type(self) -> str:
        """Determine invocation type based on attributes"""
        if self.function:
            return "function"
        elif self.component:
            return "component"
        elif self.url:
            return "http"
        elif self.endpoint:
            # Could be GraphQL, SOAP, etc. (Phase 2)
            return "endpoint"
        elif self.service:
            # Service discovery (Phase 2)
            return "service"
        else:
            return "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "invoke",
            "name": self.name,
            "invocation_type": self.get_invocation_type(),
            "function": self.function,
            "component": self.component,
            "url": self.url,
            "method": self.method,
            "headers": [h.to_dict() for h in self.headers],
            "params": [p.__dict__ for p in self.params],
            "auth_type": self.auth_type,
            "timeout": self.timeout,
            "retry": self.retry,
            "cache": self.cache
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Invoke name is required")

        # Validate that at least one target is specified
        targets = [self.function, self.component, self.url, self.endpoint, self.service]
        if not any(targets):
            errors.append("Invoke requires one of: function, component, url, endpoint, or service")

        # Validate that only one target is specified
        if sum(1 for t in targets if t is not None) > 1:
            errors.append("Invoke can only specify one target (function, component, url, endpoint, or service)")

        # Validate HTTP method
        if self.method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
            errors.append(f"Invalid HTTP method: {self.method}")

        # Validate auth_type
        if self.auth_type and self.auth_type not in ['bearer', 'apikey', 'basic', 'oauth2']:
            errors.append(f"Invalid auth_type: {self.auth_type}. Must be bearer, apikey, basic, or oauth2")

        # Validate headers
        for header in self.headers:
            errors.extend(header.validate())

        # Validate params
        for param in self.params:
            errors.extend(param.validate())

        return errors


class InvokeHeaderNode(QuantumNode):
    """Represents a header in <q:invoke>"""

    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "invokeHeader",
            "name": self.name,
            "value": self.value[:50] + "..." if len(str(self.value)) > 50 else self.value
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Header name is required")
        if self.value is None:
            errors.append(f"Header '{self.name}' value is required")
        return errors
