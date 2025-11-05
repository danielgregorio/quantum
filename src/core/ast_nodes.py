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

        # Phase G: Authentication & Security
        self.require_auth = False  # Require authentication to access component
        self.require_role = None   # Required role(s) to access (comma-separated: "admin,editor")
        self.require_permission = None  # Required permission(s)

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


# ============================================
# FORMS & ACTIONS NODES (Phase A)
# ============================================

class ActionNode(QuantumNode):
    """
    Represents a server-side action handler for forms.

    Phase A: Forms & Actions
    Actions handle POST/PUT/DELETE requests with automatic form data binding,
    validation, and redirect support.

    Examples:
      <q:action name="createUser" method="POST">
        <q:param name="email" type="email" required="true" />
        <q:param name="password" type="string" minlength="8" />
        <q:query datasource="db">
          INSERT INTO users (email, password) VALUES (:email, :password)
        </q:query>
        <q:redirect url="/users" />
      </q:action>

      <q:action name="deleteProduct" method="DELETE">
        <q:param name="id" type="integer" required="true" />
        <q:query datasource="db">
          DELETE FROM products WHERE id = :id
        </q:query>
        <q:redirect url="/products" flash="Product deleted successfully" />
      </q:action>
    """

    def __init__(
        self,
        name: str,
        method: str = "POST"
    ):
        self.name = name
        self.method = method.upper()
        self.params: List[QuantumParam] = []
        self.body: List[QuantumNode] = []

        # Action configuration
        self.validate_csrf = True  # Auto CSRF protection
        self.rate_limit = None     # e.g., "10/minute"
        self.require_auth = False  # Require authentication

    def add_param(self, param: QuantumParam):
        """Add parameter to action"""
        self.params.append(param)

    def add_statement(self, statement: QuantumNode):
        """Add statement to action body"""
        self.body.append(statement)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "action",
            "name": self.name,
            "method": self.method,
            "params": [p.__dict__ for p in self.params],
            "body_statements": len(self.body),
            "validate_csrf": self.validate_csrf,
            "rate_limit": self.rate_limit,
            "require_auth": self.require_auth
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Action name is required")

        if self.method not in ['POST', 'PUT', 'DELETE', 'PATCH']:
            errors.append(f"Invalid action method: {self.method}. Must be POST, PUT, DELETE, or PATCH")

        # Validate params
        for param in self.params:
            errors.extend(param.validate())

        # Validate body
        for statement in self.body:
            if hasattr(statement, 'validate'):
                errors.extend(statement.validate())

        return errors

    def __repr__(self):
        return f'<ActionNode name={self.name} method={self.method}>'


class RedirectNode(QuantumNode):
    """
    Represents a redirect response.

    Phase A: Forms & Actions
    Used within actions to redirect after processing.

    Examples:
      <q:redirect url="/thank-you" />
      <q:redirect url="/users/{userId}" />
      <q:redirect url="/products" flash="Product created successfully" />
      <q:redirect url="/error" status="500" flash="An error occurred" />
    """

    def __init__(
        self,
        url: str,
        flash: Optional[str] = None,
        status: int = 302
    ):
        self.url = url
        self.flash = flash      # Flash message to show on next page
        self.status = status    # HTTP status code (302 default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "redirect",
            "url": self.url,
            "flash": self.flash,
            "status": self.status
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.url:
            errors.append("Redirect URL is required")

        # Validate status code
        if self.status not in [301, 302, 303, 307, 308]:
            errors.append(f"Invalid redirect status: {self.status}. Must be 301, 302, 303, 307, or 308")

        return errors

    def __repr__(self):
        return f'<RedirectNode url={self.url}>'


class FlashNode(QuantumNode):
    """
    Represents a flash message (temporary message shown once).

    Phase A: Forms & Actions
    Flash messages persist across redirects and are shown once.

    Examples:
      <q:flash type="success" message="User created successfully" />
      <q:flash type="error" message="{errorMessage}" />
      <q:flash type="warning">Please verify your email</q:flash>
    """

    def __init__(
        self,
        message: str,
        flash_type: str = "info"
    ):
        self.message = message
        self.flash_type = flash_type  # info, success, warning, error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "flash",
            "message": self.message,
            "flash_type": self.flash_type
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.message:
            errors.append("Flash message is required")

        if self.flash_type not in ['info', 'success', 'warning', 'error']:
            errors.append(f"Invalid flash type: {self.flash_type}. Must be info, success, warning, or error")

        return errors

    def __repr__(self):
        return f'<FlashNode type={self.flash_type}>'


class FileNode(QuantumNode):
    """
    Represents file upload handling (q:file).
    
    Phase H: File Uploads
    Handles file uploads with validation and storage.
    
    Examples:
      <q:file action="upload" file="{avatar}" destination="./uploads/" />
      <q:file action="upload" file="{document}" destination="./files/" nameConflict="makeUnique" />
    """
    
    def __init__(
        self,
        action: str,
        file: str,
        destination: str = "./uploads/",
        name_conflict: str = "error",  # error, overwrite, skip, makeUnique
        result: str = None
    ):
        self.action = action  # upload, delete, move, copy
        self.file = file  # Variable name containing file data
        self.destination = destination  # Where to save file
        self.name_conflict = name_conflict  # What to do if file exists
        self.result = result  # Optional variable name to store upload result
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "file",
            "action": self.action,
            "file": self.file,
            "destination": self.destination,
            "name_conflict": self.name_conflict,
            "result": self.result
        }
    
    def validate(self) -> List[str]:
        errors = []
        
        if self.action not in ['upload', 'delete', 'move', 'copy']:
            errors.append(f"Invalid file action: {self.action}")
        
        if not self.file:
            errors.append("File variable is required")
        
        if self.action == 'upload' and not self.destination:
            errors.append("Destination is required for upload action")
        
        if self.name_conflict not in ['error', 'overwrite', 'skip', 'makeUnique']:
            errors.append(f"Invalid nameConflict: {self.name_conflict}")
        
        return errors
    
    def __repr__(self):
        return f'<FileNode action={self.action} file={self.file}>'


class MailNode(QuantumNode):
    """
    Represents email sending (q:mail).
    
    Phase I: Email Sending
    ColdFusion cfmail-inspired email functionality.
    
    Examples:
      <q:mail to="{email}" from="noreply@app.com" subject="Welcome!">
        <h1>Welcome {name}!</h1>
      </q:mail>
    """
    
    def __init__(
        self,
        to: str,
        subject: str,
        from_addr: str = None,
        cc: str = None,
        bcc: str = None,
        reply_to: str = None,
        type: str = "html",  # html or text
        charset: str = "UTF-8"
    ):
        self.to = to  # Recipient email(s)
        self.subject = subject  # Email subject
        self.from_addr = from_addr  # Sender email
        self.cc = cc  # CC recipients
        self.bcc = bcc  # BCC recipients
        self.reply_to = reply_to  # Reply-To address
        self.type = type  # html or text
        self.charset = charset  # Character encoding
        self.body = ""  # Email body (set from tag content)
        self.attachments = []  # List of file attachments
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "mail",
            "to": self.to,
            "subject": self.subject,
            "from": self.from_addr,
            "cc": self.cc,
            "bcc": self.bcc,
            "reply_to": self.reply_to,
            "mail_type": self.type,
            "charset": self.charset,
            "body": self.body,
            "attachments": self.attachments
        }
    
    def validate(self) -> List[str]:
        errors = []
        
        if not self.to:
            errors.append("Email recipient (to) is required")
        
        if not self.subject:
            errors.append("Email subject is required")
        
        if self.type not in ['html', 'text']:
            errors.append(f"Invalid email type: {self.type}. Must be 'html' or 'text'")
        
        return errors
    
    def __repr__(self):
        return f'<MailNode to={self.to} subject={self.subject}>'


class TransactionNode(QuantumNode):
    """
    Represents database transaction (q:transaction).
    
    Phase D: Database Backend
    Ensures atomic operations - all queries succeed or all rollback.
    
    Examples:
      <q:transaction>
        <q:query>UPDATE accounts SET balance = balance - 100 WHERE id = 1</q:query>
        <q:query>UPDATE accounts SET balance = balance + 100 WHERE id = 2</q:query>
      </q:transaction>
    """
    
    def __init__(
        self,
        isolation_level: str = "READ_COMMITTED"
    ):
        self.isolation_level = isolation_level  # READ_UNCOMMITTED, READ_COMMITTED, REPEATABLE_READ, SERIALIZABLE
        self.statements: List[QuantumNode] = []  # Queries and other statements inside transaction
    
    def add_statement(self, statement: QuantumNode):
        """Add statement to transaction"""
        self.statements.append(statement)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "transaction",
            "isolation_level": self.isolation_level,
            "statements": [s.to_dict() if hasattr(s, 'to_dict') else str(s) for s in self.statements]
        }
    
    def validate(self) -> List[str]:
        errors = []
        
        if not self.statements:
            errors.append("Transaction must contain at least one statement")
        
        valid_levels = ['READ_UNCOMMITTED', 'READ_COMMITTED', 'REPEATABLE_READ', 'SERIALIZABLE']
        if self.isolation_level not in valid_levels:
            errors.append(f"Invalid isolation level: {self.isolation_level}")
        
        return errors
    
    def __repr__(self):
        return f'<TransactionNode isolation={self.isolation_level} statements={len(self.statements)}>'
