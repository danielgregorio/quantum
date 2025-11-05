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


# MIGRATED: IfNode moved to feature-based structure
# Import from new location (Option C migration)
from .features.conditionals.src.ast_node import IfNode


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

        # HTML rendering & interactivity (Phase 1 & future Phase 3)
        self.interactive = False  # Enable client-side hydration (future)
        self.has_html = False     # Auto-detected if component contains HTML nodes

        # Component elements
        self.params: List[QuantumParam] = []
        self.returns: List[QuantumReturn] = []
        self.functions: List['FunctionNode'] = []
        self.event_handlers: List['OnEventNode'] = []
        self.script_blocks: List[str] = []
        self.statements: List[QuantumNode] = []  # For control flow statements (includes HTML nodes)

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
            "interactive": self.interactive,
            "has_html": self.has_html,
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


# MIGRATED: LoopNode moved to feature-based structure
# Import from new location (Option C migration)
from .features.loops.src.ast_node import LoopNode

# MIGRATED: FunctionNode and RestConfig moved to feature-based structure
# Import from new location (Option C migration)
from .features.functions.src.ast_node import FunctionNode, RestConfig




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


class QueryNode(QuantumNode):
    """Represents a <q:query> - Database query component"""

    def __init__(self, name: str, datasource: str, sql: str, params: List['QueryParamNode'] = None):
        self.name = name
        self.datasource = datasource
        self.sql = sql
        self.params = params or []

        # Optional attributes
        self.source = None  # For Query-of-Queries
        self.cache = False
        self.ttl = None
        self.reactive = False
        self.interval = None
        self.paginate = False  # Enable automatic pagination
        self.page = None
        self.page_size = 20
        self.timeout = None
        self.maxrows = None
        self.result = None  # Variable name for metadata

    def add_param(self, param: 'QueryParamNode'):
        """Add parameter to query"""
        self.params.append(param)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "query",
            "name": self.name,
            "datasource": self.datasource,
            "sql": self.sql[:50] + "..." if len(self.sql) > 50 else self.sql,
            "params": [p.to_dict() for p in self.params],
            "cache": self.cache,
            "reactive": self.reactive
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Query name is required")
        if not self.datasource and not self.source:
            errors.append("Query requires either 'datasource' or 'source' attribute")
        if not self.sql:
            errors.append("Query SQL is required")

        # Validate params
        for param in self.params:
            errors.extend(param.validate())

        return errors


class QueryParamNode(QuantumNode):
    """Represents a <q:param> within q:query"""

    def __init__(self, name: str, value: Any, param_type: str):
        self.name = name
        self.value = value
        self.param_type = param_type  # string, integer, decimal, boolean, datetime, date, time, array, json

        # Optional attributes
        self.null = False
        self.max_length = None
        self.scale = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "queryParam",
            "name": self.name,
            "value": str(self.value)[:20] + "..." if self.value and len(str(self.value)) > 20 else self.value,
            "param_type": self.param_type,
            "null": self.null
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Query parameter name is required")
        if self.value is None and not self.null:
            errors.append(f"Query parameter '{self.name}' cannot be null")
        if self.param_type not in ['string', 'integer', 'decimal', 'boolean', 'datetime', 'date', 'time', 'array', 'json']:
            errors.append(f"Invalid parameter type: {self.param_type}")

        return errors


# MIGRATED: InvokeNode and InvokeHeaderNode moved to feature-based structure
# Import from new location (Option C migration)
from .features.invocation.src.ast_node import InvokeNode, InvokeHeaderNode

# MIGRATED: DataNode and related nodes moved to feature-based structure
# Import from new location (Option C migration)
from .features.data_import.src.ast_node import (
    DataNode, ColumnNode, FieldNode, TransformNode,
    FilterNode, SortNode, LimitNode, ComputeNode, HeaderNode
)


# ============================================
# HTML RENDERING NODES (Phase 1)
# ============================================

# HTML void elements that are self-closing
HTML_VOID_ELEMENTS = {
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'param', 'source', 'track', 'wbr'
}


class HTMLNode(QuantumNode):
    """
    Represents an HTML element that should be rendered to output.

    Phase 1: Server-side rendering only
    Phase 3: Can be marked for client-side hydration

    Examples:
      <div class="container">...</div>
      <img src="/logo.png" />
      <a href="/about">About</a>
      <button q:click="handleClick">Click me</button> (future)
    """

    def __init__(
        self,
        tag: str,
        attributes: Optional[Dict[str, str]] = None,
        children: Optional[List[QuantumNode]] = None,
        self_closing: bool = False
    ):
        self.tag = tag
        self.attributes = attributes or {}
        self.children = children or []
        self.self_closing = self_closing or tag in HTML_VOID_ELEMENTS

        # Future: client-side event handlers (Phase 3)
        self.has_events = self._detect_event_handlers()

    def _detect_event_handlers(self) -> bool:
        """Detect if element has client-side event handlers (q:click, q:change, etc)"""
        event_attributes = ['q:click', 'q:change', 'q:input', 'q:submit', 'q:keyup', 'q:keydown']
        return any(attr in self.attributes for attr in event_attributes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "html",
            "tag": self.tag,
            "attributes": self.attributes,
            "children_count": len(self.children),
            "self_closing": self.self_closing,
            "has_events": self.has_events
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.tag:
            errors.append("HTML tag name is required")

        # Validate children
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())

        return errors

    def __repr__(self):
        return f'<HTMLNode tag={self.tag} attrs={len(self.attributes)} children={len(self.children)}>'


class TextNode(QuantumNode):
    """
    Represents raw text content, possibly with databinding expressions.

    Examples:
      "Hello World"
      "User: {user.name}"
      "Total: ${price * quantity}"
      "Items: {items.length}"
    """

    def __init__(self, content: str):
        self.content = content
        self.has_databinding = '{' in content and '}' in content

    def to_dict(self) -> Dict[str, Any]:
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return {
            "type": "text",
            "content": preview,
            "has_databinding": self.has_databinding,
            "length": len(self.content)
        }

    def validate(self) -> List[str]:
        # Text nodes are always valid
        return []

    def __repr__(self):
        preview = self.content[:30] + '...' if len(self.content) > 30 else self.content
        return f'<TextNode "{preview}">'


class DocTypeNode(QuantumNode):
    """
    Represents HTML DOCTYPE declaration.

    Example:
      <!DOCTYPE html>
    """

    def __init__(self, value: str = "html"):
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "doctype",
            "value": self.value
        }

    def validate(self) -> List[str]:
        return []

    def __repr__(self):
        return f'<DocTypeNode {self.value}>'


class CommentNode(QuantumNode):
    """
    Represents HTML/XML comments.

    Example:
      <!-- This is a comment -->
    """

    def __init__(self, content: str):
        self.content = content

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "comment",
            "content": self.content[:50] + '...' if len(self.content) > 50 else self.content
        }

    def validate(self) -> List[str]:
        return []

    def __repr__(self):
        return f'<CommentNode>'


# ============================================
# COMPONENT COMPOSITION NODES (Phase 2)
# ============================================

class ImportNode(QuantumNode):
    """
    Represents component import declaration.
    
    Phase 2: Component Composition
    
    Examples:
      <q:import component="Header" />
      <q:import component="Button" from="./components/ui" />
      <q:import component="AdminLayout" as="Layout" />
    """
    
    def __init__(
        self,
        component: str,
        from_path: Optional[str] = None,
        alias: Optional[str] = None
    ):
        self.component = component
        self.from_path = from_path
        self.alias = alias or component
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "import",
            "component": self.component,
            "from": self.from_path,
            "alias": self.alias
        }
    
    def validate(self) -> List[str]:
        errors = []
        if not self.component:
            errors.append("Component name is required for q:import")
        return errors
    
    def __repr__(self):
        return f'<ImportNode component={self.component}>'


class SlotNode(QuantumNode):
    """
    Represents content projection slot.
    
    Phase 2: Component Composition
    Allows parent components to inject content into child components.
    
    Examples:
      <q:slot />  <!-- Default slot -->
      <q:slot name="header" />  <!-- Named slot -->
      <q:slot name="footer">Default content here</q:slot>
    """
    
    def __init__(
        self,
        name: str = "default",
        default_content: Optional[List[QuantumNode]] = None
    ):
        self.name = name
        self.default_content = default_content or []
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "slot",
            "name": self.name,
            "has_default": len(self.default_content) > 0
        }
    
    def validate(self) -> List[str]:
        errors = []
        # Validate default content
        for node in self.default_content:
            if hasattr(node, 'validate'):
                errors.extend(node.validate())
        return errors
    
    def __repr__(self):
        return f'<SlotNode name={self.name}>'


class ComponentCallNode(QuantumNode):
    """
    Represents a call to another component (used internally during composition).
    
    Phase 2: Component Composition
    
    Examples:
      <Header title="Products" />
      <Button label="Save" color="green" />
      <Card title="Info">
        <p>Card content here</p>
      </Card>
    """
    
    def __init__(
        self,
        component_name: str,
        props: Optional[Dict[str, str]] = None,
        children: Optional[List[QuantumNode]] = None
    ):
        self.component_name = component_name
        self.props = props or {}
        self.children = children or []
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "component_call",
            "component": self.component_name,
            "props": self.props,
            "children_count": len(self.children)
        }
    
    def validate(self) -> List[str]:
        errors = []
        if not self.component_name:
            errors.append("Component name is required")
        
        # Validate children
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        
        return errors
    
    def __repr__(self):
        return f'<ComponentCallNode component={self.component_name} props={len(self.props)}>'
