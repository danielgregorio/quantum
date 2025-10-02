"""
Quantum AST Nodes - Classes that represent elements of the Quantum language
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

class QuantumNode(ABC):
    """Base class for all Quantum AST nodes"""
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert the node to dictionary (debug/serialization)"""
        pass
    
    @abstractmethod
    def validate(self) -> List[str]:
        """Validate the node and return list of errors"""
        pass


@dataclass
class QuantumParam:
    """Represents a <q:param>"""
    name: str
    type: str = "string"
    required: bool = False
    default: Optional[str] = None
    validation: Optional[str] = None
    description: Optional[str] = None

    # REST-specific (optional)
    source: str = "auto"  # auto, path, query, body, header, cookie

    # Validation (same as SetNode)
    validate_rule: Optional[str] = None
    pattern: Optional[str] = None
    min: Optional[Any] = None
    max: Optional[Any] = None
    minlength: Optional[int] = None
    maxlength: Optional[int] = None
    range: Optional[str] = None
    enum: Optional[str] = None

    # File upload (when type="binary")
    maxsize: Optional[str] = None
    accept: Optional[str] = None

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Param name is required")
        return errors


@dataclass
class QuantumReturn:
    """Represents a <q:return>"""
    name: Optional[str] = None
    type: str = "string" 
    value: Optional[str] = None
    description: Optional[str] = None
    
    def validate(self) -> List[str]:
        errors = []
        if not self.value:
            errors.append("Return value is required")
        return errors


@dataclass
class QuantumRoute:
    """Represents a <q:route>"""
    path: str
    method: str = "GET"
    returns: List[QuantumReturn] = None
    
    def __post_init__(self):
        if self.returns is None:
            self.returns = []
    
    def validate(self) -> List[str]:
        errors = []
        if not self.path:
            errors.append("Route path is required")
        if self.method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
            errors.append(f"Invalid HTTP method: {self.method}")
        return errors


class IfNode(QuantumNode):
    """Represents a <q:if> with elseif and else"""
    
    def __init__(self, condition: str):
        self.condition = condition
        self.if_body: List[QuantumNode] = []
        
        # Support for elseif blocks
        self.elseif_blocks: List[Dict[str, Any]] = []  # [{"condition": str, "body": List[QuantumNode]}]
        
        # Support for else block
        self.else_body: List[QuantumNode] = []
    
    def add_if_statement(self, statement: QuantumNode):
        """Add statement to if body"""
        self.if_body.append(statement)
    
    def add_elseif_block(self, condition: str, body: List[QuantumNode] = None):
        """Add elseif block"""
        self.elseif_blocks.append({
            "condition": condition,
            "body": body or []
        })
    
    def add_else_statement(self, statement: QuantumNode):
        """Add statement to else body"""
        self.else_body.append(statement)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "if",
            "condition": self.condition,
            "if_body_count": len(self.if_body),
            "elseif_count": len(self.elseif_blocks),
            "has_else": len(self.else_body) > 0
        }
    
    def validate(self) -> List[str]:
        errors = []
        if not self.condition:
            errors.append("If condition is required")
        
        # Validate all bodies
        for statement in self.if_body:
            errors.extend(statement.validate())
        
        for elseif_block in self.elseif_blocks:
            if not elseif_block["condition"]:
                errors.append("Elseif condition is required")
            for statement in elseif_block["body"]:
                errors.extend(statement.validate())
        
        for statement in self.else_body:
            errors.extend(statement.validate())
        
        return errors


class ComponentNode(QuantumNode):
    """Represents a <q:component>"""

    def __init__(self, name: str, component_type: str = "pure"):
        self.name = name
        self.component_type = component_type  # pure, microservice, event-driven, worker, websocket, graphql, grpc, serverless

        # Component-level config
        self.port = None
        self.base_path = None
        self.health_endpoint = None
        self.metrics_provider = None
        self.trace_provider = None

        # Component elements
        self.params: List[QuantumParam] = []
        self.returns: List[QuantumReturn] = []
        self.functions: List['FunctionNode'] = []
        self.event_handlers: List['OnEventNode'] = []
        self.script_blocks: List[str] = []
        self.statements: List[QuantumNode] = []  # For control flow statements

        # Resources (refs to Admin-configured resources)
        self.resources: Dict[str, str] = {}  # type -> ref_name (e.g., "database" -> "postgres-main")

    def add_param(self, param: QuantumParam):
        self.params.append(param)

    def add_return(self, return_node: QuantumReturn):
        self.returns.append(return_node)

    def add_function(self, function: 'FunctionNode'):
        function.container = self
        self.functions.append(function)

    def add_event_handler(self, handler: 'OnEventNode'):
        self.event_handlers.append(handler)

    def add_script(self, script: str):
        self.script_blocks.append(script)

    def add_statement(self, statement: QuantumNode):
        """Add control flow statement (if, loop, set, etc)"""
        self.statements.append(statement)

    def add_resource(self, resource_type: str, ref_name: str):
        """Add resource reference (from Admin panel)"""
        self.resources[resource_type] = ref_name

    def get_rest_endpoints(self) -> List['FunctionNode']:
        """Get all functions that are REST endpoints"""
        return [f for f in self.functions if f.is_rest_enabled()]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "component",
            "name": self.name,
            "component_type": self.component_type,
            "port": self.port,
            "base_path": self.base_path,
            "params": [p.__dict__ for p in self.params],
            "returns": [r.__dict__ for r in self.returns],
            "functions": [f.to_dict() for f in self.functions],
            "event_handlers": [eh.to_dict() for eh in self.event_handlers],
            "script_blocks": len(self.script_blocks),
            "statements": len(self.statements),
            "resources": self.resources
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Component name is required")

        # Validate component type
        valid_types = ['pure', 'microservice', 'event-driven', 'worker', 'websocket', 'graphql', 'grpc', 'serverless']
        if self.component_type not in valid_types:
            errors.append(f"Invalid component type: {self.component_type}. Must be one of {valid_types}")

        for param in self.params:
            errors.extend(param.validate())

        for ret in self.returns:
            errors.extend(ret.validate())

        for func in self.functions:
            errors.extend(func.validate())

        for handler in self.event_handlers:
            errors.extend(handler.validate())

        for statement in self.statements:
            errors.extend(statement.validate())

        return errors


class ApplicationNode(QuantumNode):
    """Represents a <q:application>"""
    
    def __init__(self, app_id: str, app_type: str):
        self.app_id = app_id
        self.app_type = app_type
        self.routes: List[QuantumRoute] = []
        self.components: List[ComponentNode] = []
    
    def add_route(self, route: QuantumRoute):
        self.routes.append(route)
    
    def add_component(self, component: ComponentNode):
        self.components.append(component)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "application",
            "app_id": self.app_id,
            "app_type": self.app_type,
            "routes": [r.__dict__ for r in self.routes],
            "components": [c.to_dict() for c in self.components]
        }
    
    def validate(self) -> List[str]:
        errors = []
        if not self.app_id:
            errors.append("Application ID is required")
        if not self.app_type:
            errors.append("Application type is required")
        
        for route in self.routes:
            errors.extend(route.validate())
        
        for component in self.components:
            errors.extend(component.validate())
        
        return errors


class JobNode(QuantumNode):
    """Represents a <q:job>"""
    
    def __init__(self, job_id: str, schedule: Optional[str] = None):
        self.job_id = job_id
        self.schedule = schedule
        self.tasks: List[Dict[str, Any]] = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "job",
            "job_id": self.job_id,
            "schedule": self.schedule,
            "tasks": self.tasks
        }
    
    def validate(self) -> List[str]:
        errors = []
        if not self.job_id:
            errors.append("Job ID is required")
        return errors


class LoopNode(QuantumNode):
    """Represents a <q:loop> with various types"""
    
    def __init__(self, loop_type: str, var_name: str):
        self.loop_type = loop_type    # range, array, list, object, query, while
        self.var_name = var_name      # variable name for current item
        self.index_name = None        # optional index variable
        self.items = None             # data source expression
        self.condition = None         # for while loops
        self.from_value = None        # for range loops
        self.to_value = None          # for range loops  
        self.step_value = 1           # for range loops
        self.delimiter = ","          # for list loops
        self.body: List[QuantumNode] = []  # statements inside loop
    
    def add_statement(self, statement: QuantumNode):
        self.body.append(statement)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "loop",
            "loop_type": self.loop_type,
            "var_name": self.var_name,
            "index_name": self.index_name,
            "from_value": self.from_value,
            "to_value": self.to_value,
            "step_value": self.step_value,
            "body_statements": len(self.body)
        }
    
    def validate(self) -> List[str]:
        errors = []
        if not self.var_name:
            errors.append("Loop variable name is required")
        
        if self.loop_type == 'range':
            if not self.from_value:
                errors.append("Range loop requires 'from' attribute")
            if not self.to_value:
                errors.append("Range loop requires 'to' attribute")
        elif self.loop_type in ['array', 'list', 'object']:
            if not self.items:
                errors.append(f"{self.loop_type.title()} loop requires 'items' attribute")
        
        for statement in self.body:
            errors.extend(statement.validate())
        
        return errors


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


class DispatchEventNode(QuantumNode):
    """Represents a <q:dispatchEvent> - Publish event"""

    def __init__(self, event: str):
        self.event = event
        self.data = None
        self.queue = None
        self.exchange = None
        self.routing_key = None
        self.priority = "normal"  # low, normal, high
        self.delay = None         # e.g., "5s"
        self.ttl = None          # e.g., "60s"
        self.metadata = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "dispatchEvent",
            "event": self.event,
            "data": self.data,
            "queue": self.queue,
            "exchange": self.exchange,
            "routing_key": self.routing_key,
            "priority": self.priority,
            "delay": self.delay,
            "ttl": self.ttl,
            "metadata": self.metadata
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.event:
            errors.append("Event name is required for dispatchEvent")
        if self.priority not in ['low', 'normal', 'high']:
            errors.append(f"Invalid priority: {self.priority}. Must be low, normal, or high")
        return errors


class OnEventNode(QuantumNode):
    """Represents a <q:onEvent> - Subscribe to event"""

    def __init__(self, event: str):
        self.event = event          # Event pattern (e.g., "user.*" or "user.created")
        self.queue = None
        self.max_retries = 0
        self.retry_delay = None     # e.g., "30s"
        self.dead_letter = None     # Dead letter queue
        self.filter = None          # Filter expression
        self.concurrent = 1         # Parallel processing
        self.prefetch = 1          # Prefetch count
        self.timeout = None        # Handler timeout
        self.body: List[QuantumNode] = []

    def add_statement(self, statement: QuantumNode):
        """Add statement to event handler body"""
        self.body.append(statement)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "onEvent",
            "event": self.event,
            "queue": self.queue,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "dead_letter": self.dead_letter,
            "filter": self.filter,
            "concurrent": self.concurrent,
            "prefetch": self.prefetch,
            "timeout": self.timeout,
            "body_statements": len(self.body)
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.event:
            errors.append("Event pattern is required for onEvent")

        # Validate body
        for statement in self.body:
            errors.extend(statement.validate())

        return errors


# MIGRATED: SetNode moved to feature-based structure
# Import from new location (Option C migration)
from .features.state_management.src.ast_node import SetNode
