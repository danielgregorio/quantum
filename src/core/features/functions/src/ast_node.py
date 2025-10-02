"""
AST Node for Functions (q:function)
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Import base class
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.ast_nodes import QuantumNode, QuantumParam


@dataclass
class RestConfig:
    """REST configuration for a function - OPTIONAL"""
    # Required (if REST enabled)
    endpoint: str
    method: str = "GET"

    # Optional (with sensible defaults)
    produces: str = "application/json"
    consumes: str = "application/json"
    auth: Optional[str] = None       # None = no auth, or: bearer, basic, apikey
    roles: List[str] = None          # None = no role check
    rate_limit: Optional[str] = None # "100/minute"
    cors: bool = False
    status: int = 200                # Default status code

    def __post_init__(self):
        if self.roles is None:
            self.roles = []


class FunctionNode(QuantumNode):
    """Represents a <q:function>"""

    def __init__(self, name: str):
        # ========== CORE (required) ==========
        self.name = name
        self.return_type = "any"
        self.scope = "component"  # component, global, api
        self.access = "public"    # public, private, protected
        self.params: List[QuantumParam] = []
        self.body: List[QuantumNode] = []

        # ========== OPTIONAL LAYERS ==========

        # Layer 1: Documentation
        self.description = None
        self.hint = None

        # Layer 2: Validation
        self.validate_params = False  # Auto-validate params

        # Layer 3: Performance
        self.cache = False
        self.cache_ttl = None  # seconds
        self.memoize = False
        self.pure = False

        # Layer 4: Behavior
        self.async_func = False
        self.retry = 0
        self.timeout = None  # seconds

        # Layer 5: REST API (completely optional)
        self.rest_config: Optional[RestConfig] = None

        # Back-reference to container
        self.container: Optional['ComponentNode'] = None

    def is_rest_enabled(self) -> bool:
        """Check if function has REST configuration"""
        return self.rest_config is not None

    def enable_rest(self, endpoint: str, method: str = "GET"):
        """Enable REST for this function"""
        self.rest_config = RestConfig(
            endpoint=endpoint,
            method=method
        )

    def is_private(self) -> bool:
        """Check if function is private (starts with _ or access=private)"""
        return self.access == "private" or self.name.startswith('_')

    def add_param(self, param: QuantumParam):
        """Add parameter to function"""
        self.params.append(param)

    def add_statement(self, statement: QuantumNode):
        """Add statement to function body"""
        self.body.append(statement)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "function",
            "name": self.name,
            "return_type": self.return_type,
            "scope": self.scope,
            "access": self.access,
            "params_count": len(self.params),
            "body_statements": len(self.body),
            "description": self.description,
            "validate_params": self.validate_params,
            "cache": self.cache,
            "memoize": self.memoize,
            "pure": self.pure,
            "async": self.async_func,
            "retry": self.retry,
            "timeout": self.timeout
        }

        if self.rest_config:
            result["rest"] = {
                "endpoint": self.rest_config.endpoint,
                "method": self.rest_config.method,
                "produces": self.rest_config.produces,
                "consumes": self.rest_config.consumes,
                "auth": self.rest_config.auth,
                "roles": self.rest_config.roles,
                "status": self.rest_config.status
            }

        return result

    def validate(self) -> List[str]:
        errors = []

        if not self.name:
            errors.append("Function name is required")

        # Validate params
        for param in self.params:
            errors.extend(param.validate())

        # Validate body
        for statement in self.body:
            errors.extend(statement.validate())

        # Validate REST config if present
        if self.rest_config:
            if not self.rest_config.endpoint:
                errors.append("REST endpoint is required when REST is enabled")
            if self.rest_config.method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                errors.append(f"Invalid HTTP method: {self.rest_config.method}")

        return errors
