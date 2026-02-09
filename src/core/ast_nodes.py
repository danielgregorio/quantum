"""
Quantum AST Nodes - Classes that represent elements of the Quantum language
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field


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
        self.engine: Optional[str] = None  # "2d" for game engine
        self.routes: List[QuantumRoute] = []
        self.components: List[ComponentNode] = []

        # Game Engine 2D: game-specific children
        self.scenes: List[QuantumNode] = []     # SceneNode list
        self.behaviors: List[QuantumNode] = []   # BehaviorNode list
        self.prefabs: List[QuantumNode] = []     # PrefabNode list

        # Terminal Engine: terminal-specific children
        self.screens: List[QuantumNode] = []      # ScreenNode list
        self.keybindings: List[QuantumNode] = []  # KeybindingNode list
        self.services: List[QuantumNode] = []     # ServiceNode list
        self.terminal_css: str = ""               # Accumulated TCSS

        # Testing Engine: testing-specific children
        self.test_suites: List[QuantumNode] = []       # TestSuiteNode list
        self.test_config: Optional[QuantumNode] = None  # BrowserConfigNode
        self.test_fixtures: List[QuantumNode] = []     # FixtureNode_Testing list
        self.test_mocks: List[QuantumNode] = []        # MockNode_Testing list
        self.test_auth_states: List[QuantumNode] = []  # AuthNode list

        # UI Engine: multi-target UI children
        self.ui_windows: List[QuantumNode] = []    # UIWindowNode list
        self.ui_children: List[QuantumNode] = []   # Top-level UI nodes (no window)
        self.ui_target: str = 'html'               # html, textual, desktop
        self.ui_theme: Optional[QuantumNode] = None  # UIThemeNode (from ui:theme or theme attr)
        self.ui_theme_preset: Optional[str] = None   # Theme preset from theme attribute

    def add_route(self, route: QuantumRoute):
        self.routes.append(route)

    def add_component(self, component: ComponentNode):
        self.components.append(component)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "application",
            "app_id": self.app_id,
            "app_type": self.app_type,
            "engine": self.engine,
            "routes": [r.__dict__ for r in self.routes],
            "components": [c.to_dict() for c in self.components],
        }
        if self.scenes:
            result["scenes"] = [s.to_dict() for s in self.scenes]
        if self.behaviors:
            result["behaviors"] = [b.to_dict() for b in self.behaviors]
        if self.prefabs:
            result["prefabs"] = [p.to_dict() for p in self.prefabs]
        if self.screens:
            result["screens"] = [s.to_dict() for s in self.screens]
        if self.keybindings:
            result["keybindings"] = [k.to_dict() for k in self.keybindings]
        if self.services:
            result["services"] = [s.to_dict() for s in self.services]
        if self.terminal_css:
            result["terminal_css"] = self.terminal_css
        if self.test_suites:
            result["test_suites"] = [s.to_dict() for s in self.test_suites]
        if self.test_config:
            result["test_config"] = self.test_config.to_dict()
        if self.test_fixtures:
            result["test_fixtures"] = [f.to_dict() for f in self.test_fixtures]
        if self.test_mocks:
            result["test_mocks"] = [m.to_dict() for m in self.test_mocks]
        if self.test_auth_states:
            result["test_auth_states"] = [a.to_dict() for a in self.test_auth_states]
        if self.ui_windows:
            result["ui_windows"] = [w.to_dict() for w in self.ui_windows]
        if self.ui_children:
            result["ui_children"] = [c.to_dict() for c in self.ui_children]
        if self.ui_target != 'html':
            result["ui_target"] = self.ui_target
        if self.ui_theme:
            result["ui_theme"] = self.ui_theme.to_dict()
        if self.ui_theme_preset:
            result["ui_theme_preset"] = self.ui_theme_preset
        return result

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

        # Validate game children
        for scene in self.scenes:
            if hasattr(scene, 'validate'):
                errors.extend(scene.validate())
        for behavior in self.behaviors:
            if hasattr(behavior, 'validate'):
                errors.extend(behavior.validate())
        for prefab in self.prefabs:
            if hasattr(prefab, 'validate'):
                errors.extend(prefab.validate())

        # Validate terminal children
        for screen in self.screens:
            if hasattr(screen, 'validate'):
                errors.extend(screen.validate())
        for keybinding in self.keybindings:
            if hasattr(keybinding, 'validate'):
                errors.extend(keybinding.validate())
        for service in self.services:
            if hasattr(service, 'validate'):
                errors.extend(service.validate())

        # Validate testing children
        for suite in self.test_suites:
            if hasattr(suite, 'validate'):
                errors.extend(suite.validate())
        if self.test_config and hasattr(self.test_config, 'validate'):
            errors.extend(self.test_config.validate())
        for fixture in self.test_fixtures:
            if hasattr(fixture, 'validate'):
                errors.extend(fixture.validate())
        for mock in self.test_mocks:
            if hasattr(mock, 'validate'):
                errors.extend(mock.validate())
        for auth in self.test_auth_states:
            if hasattr(auth, 'validate'):
                errors.extend(auth.validate())

        # Validate UI children
        for window in self.ui_windows:
            if hasattr(window, 'validate'):
                errors.extend(window.validate())
        for ui_child in self.ui_children:
            if hasattr(ui_child, 'validate'):
                errors.extend(ui_child.validate())

        return errors


class JobNode(QuantumNode):
    """
    Represents a <q:job> - Job queue for batch processing.

    Examples:
      <q:job name="sendEmail" queue="emails" priority="5">
        <q:param name="to" type="string" />
        <q:param name="subject" type="string" />
        <q:mail to="{to}" subject="{subject}">...</q:mail>
      </q:job>

      <q:job name="processOrder" action="dispatch" delay="5m" />
    """

    def __init__(self, name: str, queue: str = 'default', action: str = 'define'):
        self.name = name
        self.queue = queue
        self.action = action  # define, dispatch, batch
        self.delay: Optional[str] = None  # e.g., '30s', '5m', '1h'
        self.priority: int = 0
        self.attempts: int = 3
        self.backoff: str = '30s'
        self.timeout: Optional[str] = None
        self.params: List['QuantumParam'] = []
        self.body: List['QuantumNode'] = []

        # Legacy compatibility
        self.job_id: Optional[str] = name
        self.schedule: Optional[str] = None
        self.tasks: List[Dict[str, Any]] = []

    def add_param(self, param: 'QuantumParam'):
        """Add parameter to job"""
        self.params.append(param)

    def add_statement(self, statement: 'QuantumNode'):
        """Add statement to job body"""
        self.body.append(statement)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "job",
            "name": self.name,
            "queue": self.queue,
            "action": self.action,
            "delay": self.delay,
            "priority": self.priority,
            "attempts": self.attempts,
            "backoff": self.backoff,
            "timeout": self.timeout,
            "params": [p.__dict__ for p in self.params],
            "body_statements": len(self.body),
            # Legacy
            "job_id": self.job_id,
            "schedule": self.schedule,
            "tasks": self.tasks
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Job name is required")
        if self.action not in ['define', 'dispatch', 'batch']:
            errors.append(f"Invalid job action: {self.action}. Must be define, dispatch, or batch")
        if self.priority < 0 or self.priority > 10:
            errors.append(f"Job priority must be between 0 and 10")
        for param in self.params:
            errors.extend(param.validate())
        for statement in self.body:
            if hasattr(statement, 'validate'):
                errors.extend(statement.validate())
        return errors

    def __repr__(self):
        return f'<JobNode name={self.name} queue={self.queue} action={self.action}>'


@dataclass
class ScheduleNode(QuantumNode):
    """
    Represents a <q:schedule> - Scheduled task execution (like cfschedule).

    Examples:
      <q:schedule name="dailyReport" interval="1d" timezone="America/Sao_Paulo">
        <q:query datasource="db" name="stats">SELECT * FROM daily_stats</q:query>
        <q:mail to="admin@example.com" subject="Daily Report">...</q:mail>
      </q:schedule>

      <q:schedule name="cleanup" cron="0 2 * * *" retry="3">
        <q:query datasource="db">DELETE FROM temp_data WHERE created_at < NOW() - INTERVAL 7 DAY</q:query>
      </q:schedule>

      <q:schedule name="oneTimeTask" at="2024-12-25T00:00:00" enabled="true" />
    """
    name: str
    action: str = 'run'  # run, pause, resume, delete
    interval: Optional[str] = None  # 30s, 5m, 1h, 1d
    cron: Optional[str] = None  # cron expression
    at: Optional[str] = None  # specific datetime (ISO 8601)
    timezone: str = 'UTC'
    retry: int = 3
    timeout: Optional[str] = None
    overlap: bool = False  # Allow overlapping executions
    enabled: bool = True
    body: List['QuantumNode'] = field(default_factory=list)

    def add_statement(self, statement: 'QuantumNode'):
        """Add statement to schedule body"""
        self.body.append(statement)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "schedule",
            "name": self.name,
            "action": self.action,
            "interval": self.interval,
            "cron": self.cron,
            "at": self.at,
            "timezone": self.timezone,
            "retry": self.retry,
            "timeout": self.timeout,
            "overlap": self.overlap,
            "enabled": self.enabled,
            "body_statements": len(self.body)
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Schedule name is required")
        if self.action not in ['run', 'pause', 'resume', 'delete']:
            errors.append(f"Invalid schedule action: {self.action}. Must be run, pause, resume, or delete")
        # Must have at least one trigger type for 'run' action
        if self.action == 'run' and not (self.interval or self.cron or self.at):
            errors.append("Schedule requires 'interval', 'cron', or 'at' attribute for run action")
        if self.retry < 0:
            errors.append("Schedule retry must be non-negative")
        for statement in self.body:
            if hasattr(statement, 'validate'):
                errors.extend(statement.validate())
        return errors

    def __repr__(self):
        trigger = self.interval or self.cron or self.at or 'none'
        return f'<ScheduleNode name={self.name} trigger={trigger}>'


@dataclass
class ThreadNode(QuantumNode):
    """
    Represents a <q:thread> - Async thread execution (like cfthread).

    Examples:
      <q:thread name="sendEmails" priority="high">
        <q:loop query="pendingEmails">
          <q:mail to="{email}" subject="Notification">...</q:mail>
        </q:loop>
      </q:thread>

      <q:thread name="processImages" timeout="5m" onComplete="handleComplete">
        <q:invoke url="/api/process" method="POST" />
      </q:thread>

      <q:thread name="worker1" action="join" />  <!-- Wait for thread -->
      <q:thread name="worker1" action="terminate" />  <!-- Kill thread -->
    """
    name: str
    action: str = 'run'  # run, join, terminate
    priority: str = 'normal'  # low, normal, high
    timeout: Optional[str] = None  # e.g., '30s', '5m'
    on_complete: Optional[str] = None  # Callback function name
    on_error: Optional[str] = None  # Error handler function name
    body: List['QuantumNode'] = field(default_factory=list)

    def add_statement(self, statement: 'QuantumNode'):
        """Add statement to thread body"""
        self.body.append(statement)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "thread",
            "name": self.name,
            "action": self.action,
            "priority": self.priority,
            "timeout": self.timeout,
            "on_complete": self.on_complete,
            "on_error": self.on_error,
            "body_statements": len(self.body)
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Thread name is required")
        if self.action not in ['run', 'join', 'terminate']:
            errors.append(f"Invalid thread action: {self.action}. Must be run, join, or terminate")
        if self.priority not in ['low', 'normal', 'high']:
            errors.append(f"Invalid thread priority: {self.priority}. Must be low, normal, or high")
        # Body required only for 'run' action
        if self.action == 'run' and not self.body:
            errors.append("Thread with action='run' requires body statements")
        for statement in self.body:
            if hasattr(statement, 'validate'):
                errors.extend(statement.validate())
        return errors

    def __repr__(self):
        return f'<ThreadNode name={self.name} action={self.action} priority={self.priority}>'


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


# MIGRATED: SetNode and PersistNode moved to feature-based structure
# Import from new location (Option C migration)
from .features.state_management.src.ast_node import SetNode, PersistNode


class QueryNode(QuantumNode):
    """Represents a <q:query> - Database query component"""

    def __init__(self, name: str, datasource: str, sql: str, params: List['QueryParamNode'] = None):
        self.name = name
        self.datasource = datasource
        self.sql = sql
        self.params = params or []

        # Optional attributes
        self.source = None  # For Query-of-Queries
        self.mode = None    # None for normal, "rag" for RAG pipeline
        self.rag_model = None  # LLM model override for RAG queries
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


# MIGRATED: KnowledgeNode moved to feature-based structure
# Import from new location (Option C migration)
from .features.knowledge_base.src import KnowledgeNode, KnowledgeSourceNode

# GAME ENGINE 2D: Import game AST nodes
from .features.game_engine_2d.src.ast_nodes import (
    SceneNode, SpriteNode, PhysicsNode, ColliderNode, AnimationNode,
    CameraNode, InputNode, SoundNode, ParticleNode, TimerNode,
    SpawnNode, HudNode, TweenNode, TilemapNode, TilemapLayerNode,
    BehaviorNode, UseNode, PrefabNode, InstanceNode, GroupNode,
    StateMachineNode, StateNode, TransitionNode,
)


class LLMMessageNode(QuantumNode):
    """
    Represents <q:message> inside <q:llm> for chat mode.

    Examples:
      <q:message role="system">You are a helpful assistant</q:message>
      <q:message role="user">{userQuestion}</q:message>
    """

    def __init__(self, role: str, content: str):
        self.role = role       # "system", "user", "assistant"
        self.content = content

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "llm_message",
            "role": self.role,
            "content": self.content[:50] + '...' if len(self.content) > 50 else self.content
        }

    def validate(self) -> List[str]:
        errors = []
        if self.role not in ['system', 'user', 'assistant']:
            errors.append(f"Invalid message role: {self.role}. Must be system, user, or assistant")
        if not self.content:
            errors.append("Message content is required")
        return errors

    def __repr__(self):
        return f'<LLMMessageNode role={self.role}>'


class LLMNode(QuantumNode):
    """
    Represents <q:llm> - LLM invocation via Ollama/compatible API.

    Examples:
      <q:llm name="greeting" model="phi3">
        <q:prompt>Say hello to {userName}</q:prompt>
      </q:llm>

      <q:llm name="chat" model="mistral">
        <q:message role="system">You are a helpful assistant</q:message>
        <q:message role="user">{question}</q:message>
      </q:llm>

      <q:llm name="data" model="llama3" responseFormat="json">
        <q:prompt>Extract name and age from: {text}</q:prompt>
      </q:llm>
    """

    def __init__(self, name: str):
        self.name = name               # Result variable name
        self.model = None               # e.g. "phi3", "mistral", "llama3"
        self.endpoint = None            # Override base URL (optional)
        self.prompt = None              # Prompt text (with databinding)
        self.system = None              # System prompt (optional)
        self.messages: List[LLMMessageNode] = []  # Chat mode messages
        self.temperature = None         # 0.0-2.0
        self.max_tokens = None          # Token limit
        self.response_format = None     # "text" or "json"
        self.cache = False
        self.timeout = 30

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "llm",
            "name": self.name,
            "model": self.model,
            "endpoint": self.endpoint,
            "prompt": self.prompt[:50] + '...' if self.prompt and len(self.prompt) > 50 else self.prompt,
            "system": self.system,
            "messages": [m.to_dict() for m in self.messages],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": self.response_format,
            "cache": self.cache,
            "timeout": self.timeout
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("LLM name (result variable) is required")
        if not self.prompt and not self.messages:
            errors.append("LLM requires either a <q:prompt> or <q:message> children")
        for msg in self.messages:
            errors.extend(msg.validate())
        return errors

    def __repr__(self):
        mode = "chat" if self.messages else "completion"
        return f'<LLMNode name={self.name} model={self.model} mode={mode}>'


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


class InvokeHeaderNode(QuantumNode):
    """
    Represents an HTTP header within q:invoke.

    Example:
      <q:invoke url="..." method="POST">
        <q:header name="Authorization" value="Bearer {token}" />
      </q:invoke>
    """

    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "invoke_header",
            "name": self.name,
            "value": self.value
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Invoke header requires 'name' attribute")
        if self.value is None:
            errors.append(f"Invoke header '{self.name}' requires 'value' attribute")
        return errors

    def __repr__(self):
        return f'<InvokeHeaderNode name={self.name}>'


class HeaderNode(QuantumNode):
    """
    Represents an HTTP header for data sources (q:data).

    Example:
      <q:data name="api_data" source="https://api.example.com/data" type="json">
        <q:header name="Authorization" value="Bearer {token}" />
      </q:data>
    """

    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "header",
            "name": self.name,
            "value": self.value
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Header requires 'name' attribute")
        if self.value is None:
            errors.append(f"Header '{self.name}' requires 'value' attribute")
        return errors

    def __repr__(self):
        return f'<HeaderNode name={self.name}>'


class ColumnNode(QuantumNode):
    """
    Represents a column definition for CSV data import.

    Example:
      <q:data name="users" source="users.csv" type="csv">
        <q:column name="id" type="integer" required="true" />
        <q:column name="email" type="string" validate="email" />
        <q:column name="age" type="integer" min="0" max="150" />
      </q:data>
    """

    def __init__(self, name: str, col_type: str = 'string'):
        self.name = name
        self.col_type = col_type
        self.required: bool = False
        self.default: Optional[str] = None
        self.validate_rule: Optional[str] = None
        self.pattern: Optional[str] = None
        self.min: Optional[Union[int, float, str]] = None
        self.max: Optional[Union[int, float, str]] = None
        self.minlength: Optional[int] = None
        self.maxlength: Optional[int] = None
        self.range: Optional[str] = None
        self.enum: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "column",
            "name": self.name,
            "col_type": self.col_type,
            "required": self.required,
            "default": self.default,
            "validate_rule": self.validate_rule,
            "pattern": self.pattern,
            "min": self.min,
            "max": self.max,
            "minlength": self.minlength,
            "maxlength": self.maxlength,
            "range": self.range,
            "enum": self.enum
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Column requires 'name' attribute")
        return errors

    def __repr__(self):
        return f'<ColumnNode name={self.name} type={self.col_type}>'


class FieldNode(QuantumNode):
    """
    Represents a field mapping for XML data import.

    Example:
      <q:data name="catalog" source="products.xml" type="xml">
        <q:field name="id" xpath="//product/@id" type="integer" />
        <q:field name="name" xpath="//product/name/text()" />
      </q:data>
    """

    def __init__(self, name: str, xpath: str, field_type: str = 'string'):
        self.name = name
        self.xpath = xpath
        self.field_type = field_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "field",
            "name": self.name,
            "xpath": self.xpath,
            "field_type": self.field_type
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Field requires 'name' attribute")
        if not self.xpath:
            errors.append("Field requires 'xpath' attribute")
        return errors

    def __repr__(self):
        return f'<FieldNode name={self.name} xpath={self.xpath}>'


class FilterNode(QuantumNode):
    """
    Represents a filter operation in data transformation.

    Example:
      <q:transform>
        <q:filter condition="age >= 18" />
      </q:transform>
    """

    def __init__(self, condition: str):
        self.condition = condition

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "filter",
            "condition": self.condition
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.condition:
            errors.append("Filter requires 'condition' attribute")
        return errors

    def __repr__(self):
        return f'<FilterNode condition={self.condition}>'


class SortNode(QuantumNode):
    """
    Represents a sort operation in data transformation.

    Example:
      <q:transform>
        <q:sort by="name" order="asc" />
      </q:transform>
    """

    def __init__(self, by: str, order: str = 'asc'):
        self.by = by
        self.order = order

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "sort",
            "by": self.by,
            "order": self.order
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.by:
            errors.append("Sort requires 'by' attribute")
        if self.order not in ('asc', 'desc'):
            errors.append(f"Sort order must be 'asc' or 'desc', got: {self.order}")
        return errors

    def __repr__(self):
        return f'<SortNode by={self.by} order={self.order}>'


class LimitNode(QuantumNode):
    """
    Represents a limit operation in data transformation.

    Example:
      <q:transform>
        <q:limit value="10" />
      </q:transform>
    """

    def __init__(self, value: int):
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "limit",
            "value": self.value
        }

    def validate(self) -> List[str]:
        errors = []
        if not isinstance(self.value, int) or self.value < 0:
            errors.append("Limit value must be a non-negative integer")
        return errors

    def __repr__(self):
        return f'<LimitNode value={self.value}>'


class ComputeNode(QuantumNode):
    """
    Represents a compute operation in data transformation.

    Example:
      <q:transform>
        <q:compute field="full_name" expression="first_name + ' ' + last_name" />
      </q:transform>
    """

    def __init__(self, field: str, expression: str, comp_type: str = 'string'):
        self.field = field
        self.expression = expression
        self.comp_type = comp_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "compute",
            "field": self.field,
            "expression": self.expression,
            "comp_type": self.comp_type
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.field:
            errors.append("Compute requires 'field' attribute")
        if not self.expression:
            errors.append("Compute requires 'expression' attribute")
        return errors

    def __repr__(self):
        return f'<ComputeNode field={self.field}>'


class TransformNode(QuantumNode):
    """
    Represents a container for data transformation operations.

    Example:
      <q:data name="filtered_users" source="users.csv" type="csv">
        <q:transform>
          <q:filter condition="age >= 18" />
          <q:sort by="name" order="asc" />
          <q:limit value="100" />
        </q:transform>
      </q:data>
    """

    def __init__(self):
        self.operations: List[QuantumNode] = []

    def add_operation(self, operation: QuantumNode):
        """Add a transformation operation (filter, sort, limit, compute)"""
        self.operations.append(operation)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "transform",
            "operations": [op.to_dict() for op in self.operations]
        }

    def validate(self) -> List[str]:
        errors = []
        for op in self.operations:
            errors.extend(op.validate())
        return errors

    def __repr__(self):
        return f'<TransformNode operations={len(self.operations)}>'


class DataNode(QuantumNode):
    """
    Represents a data import statement (q:data).

    Supports importing data from various sources:
    - CSV files
    - XML files
    - JSON APIs
    - Excel files

    Example:
      <q:data name="users" source="users.csv" type="csv" delimiter="," header="true">
        <q:column name="id" type="integer" />
        <q:column name="name" type="string" />
        <q:transform>
          <q:filter condition="id > 0" />
        </q:transform>
      </q:data>
    """

    def __init__(self, name: str, source: str, data_type: str = 'csv'):
        self.name = name
        self.source = source
        self.data_type = data_type

        # Caching options
        self.cache: bool = True
        self.ttl: Optional[int] = None

        # CSV-specific options
        self.delimiter: str = ','
        self.quote: str = '"'
        self.header: bool = True
        self.encoding: str = 'utf-8'
        self.skip_rows: int = 0

        # XML-specific options
        self.xpath: Optional[str] = None
        self.namespace: Optional[str] = None

        # Result metadata
        self.result: Optional[str] = None

        # Child elements
        self.columns: List[ColumnNode] = []
        self.fields: List[FieldNode] = []
        self.transforms: List[TransformNode] = []
        self.headers: List[HeaderNode] = []

    def add_column(self, column: 'ColumnNode'):
        """Add a column definition (for CSV)"""
        self.columns.append(column)

    def add_field(self, field: 'FieldNode'):
        """Add a field mapping (for XML)"""
        self.fields.append(field)

    def add_transform(self, transform: 'TransformNode'):
        """Add a transform container"""
        self.transforms.append(transform)

    def add_header(self, header: 'HeaderNode'):
        """Add an HTTP header (for remote sources)"""
        self.headers.append(header)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "data",
            "name": self.name,
            "source": self.source,
            "data_type": self.data_type,
            "cache": self.cache,
            "ttl": self.ttl,
            "delimiter": self.delimiter,
            "quote": self.quote,
            "header": self.header,
            "encoding": self.encoding,
            "skip_rows": self.skip_rows,
            "xpath": self.xpath,
            "namespace": self.namespace,
            "result": self.result,
            "columns": [c.to_dict() for c in self.columns],
            "fields": [f.to_dict() for f in self.fields],
            "transforms": [t.to_dict() for t in self.transforms],
            "headers": [h.to_dict() for h in self.headers]
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Data requires 'name' attribute")
        if not self.source:
            errors.append("Data requires 'source' attribute")

        for col in self.columns:
            errors.extend(col.validate())
        for field in self.fields:
            errors.extend(field.validate())
        for transform in self.transforms:
            errors.extend(transform.validate())
        for header in self.headers:
            errors.extend(header.validate())

        return errors

    def __repr__(self):
        return f'<DataNode name={self.name} source={self.source} type={self.data_type}>'


# ============================================
# MESSAGE QUEUE NODES (Phase: Message Queue System)
# ============================================

@dataclass
class MessageHeaderNode(QuantumNode):
    """
    Represents a message header for q:message.

    Example:
      <q:message topic="orders.created">
        <q:header name="priority" value="high" />
        <q:header name="correlation-id" value="{requestId}" />
      </q:message>
    """
    name: str = ""
    value: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "message_header",
            "name": self.name,
            "value": self.value
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Message header requires 'name' attribute")
        return errors

    def __repr__(self):
        return f'<MessageHeaderNode name={self.name}>'


@dataclass
class MessageNode(QuantumNode):
    """
    Represents a message publish/send operation (q:message).

    Supports three modes:
    - publish: Pub/Sub to a topic (fanout)
    - send: Direct queue send (point-to-point)
    - request: Request/reply pattern with timeout

    Examples:
      <!-- Publish to topic -->
      <q:message name="result" topic="orders.created" type="publish">
        <q:body>{orderData}</q:body>
      </q:message>

      <!-- Send to queue -->
      <q:message name="taskId" queue="email-queue" type="send">
        <q:header name="priority" value="high" />
        <q:body>{"to": "{email}", "subject": "Welcome!"}</q:body>
      </q:message>

      <!-- Request/reply -->
      <q:message name="response" queue="calculator" type="request" timeout="5000">
        <q:body>{"operation": "add", "a": 5, "b": 3}</q:body>
      </q:message>
    """
    name: Optional[str] = None  # result variable name
    topic: Optional[str] = None  # for pub/sub
    queue: Optional[str] = None  # for direct queue
    type: str = 'publish'  # publish, send, request
    timeout: Optional[str] = None  # for request type (ms)
    headers: List['MessageHeaderNode'] = field(default_factory=list)
    body: Optional[str] = None

    def add_header(self, header: 'MessageHeaderNode'):
        """Add a header to the message"""
        self.headers.append(header)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "message",
            "name": self.name,
            "topic": self.topic,
            "queue": self.queue,
            "message_type": self.type,
            "timeout": self.timeout,
            "headers": [h.to_dict() for h in self.headers],
            "body": self.body[:50] + '...' if self.body and len(self.body) > 50 else self.body
        }

    def validate(self) -> List[str]:
        errors = []

        if not self.topic and not self.queue:
            errors.append("Message requires either 'topic' or 'queue' attribute")

        if self.topic and self.queue:
            errors.append("Message cannot have both 'topic' and 'queue' attributes")

        if self.type not in ['publish', 'send', 'request']:
            errors.append(f"Invalid message type: {self.type}. Must be publish, send, or request")

        if self.type == 'request' and not self.timeout:
            # Default timeout for request type
            pass  # Will use default in runtime

        for header in self.headers:
            errors.extend(header.validate())

        return errors

    def __repr__(self):
        target = self.topic if self.topic else self.queue
        return f'<MessageNode type={self.type} target={target}>'


@dataclass
class SubscribeNode(QuantumNode):
    """
    Represents a subscription to topics or queue consumption (q:subscribe).

    Examples:
      <!-- Subscribe to topic -->
      <q:subscribe name="orderHandler" topic="orders.*" ack="auto">
        <q:onMessage>
          <q:set name="order" value="{message.body}" />
          <q:log message="Received order: {order.id}" />
        </q:onMessage>
        <q:onError>
          <q:log level="error" message="Failed to process: {error}" />
        </q:onError>
      </q:subscribe>

      <!-- Consume from queue with manual ack -->
      <q:subscribe name="emailWorker" queue="email-queue" ack="manual" prefetch="10">
        <q:onMessage>
          <q:mail to="{message.body.to}" subject="{message.body.subject}" />
          <q:messageAck />
        </q:onMessage>
      </q:subscribe>
    """
    name: str = ""
    topic: Optional[str] = None  # single topic
    topics: Optional[str] = None  # comma-separated or pattern
    queue: Optional[str] = None  # for queue consumption
    ack: str = 'auto'  # auto, manual
    prefetch: int = 1  # prefetch count
    on_message: List['QuantumNode'] = field(default_factory=list)
    on_error: List['QuantumNode'] = field(default_factory=list)

    def add_on_message_statement(self, statement: 'QuantumNode'):
        """Add statement to on_message handler"""
        self.on_message.append(statement)

    def add_on_error_statement(self, statement: 'QuantumNode'):
        """Add statement to on_error handler"""
        self.on_error.append(statement)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "subscribe",
            "name": self.name,
            "topic": self.topic,
            "topics": self.topics,
            "queue": self.queue,
            "ack": self.ack,
            "prefetch": self.prefetch,
            "on_message_count": len(self.on_message),
            "on_error_count": len(self.on_error)
        }

    def validate(self) -> List[str]:
        errors = []

        if not self.name:
            errors.append("Subscribe requires 'name' attribute")

        if not self.topic and not self.topics and not self.queue:
            errors.append("Subscribe requires 'topic', 'topics', or 'queue' attribute")

        if self.ack not in ['auto', 'manual']:
            errors.append(f"Invalid ack mode: {self.ack}. Must be 'auto' or 'manual'")

        if self.prefetch < 1:
            errors.append(f"Prefetch must be at least 1 (got {self.prefetch})")

        for statement in self.on_message:
            if hasattr(statement, 'validate'):
                errors.extend(statement.validate())

        for statement in self.on_error:
            if hasattr(statement, 'validate'):
                errors.extend(statement.validate())

        return errors

    def __repr__(self):
        target = self.topic or self.topics or self.queue
        return f'<SubscribeNode name={self.name} target={target}>'


@dataclass
class QueueNode(QuantumNode):
    """
    Represents queue/exchange declaration and management (q:queue).

    Actions:
    - declare: Create queue/exchange if not exists
    - purge: Remove all messages from queue
    - delete: Delete the queue
    - info: Get queue information (message count, consumers, etc.)

    Examples:
      <!-- Declare a durable queue -->
      <q:queue name="email-queue" action="declare" durable="true" />

      <!-- Declare with dead letter queue -->
      <q:queue name="orders" action="declare" durable="true"
               deadLetterQueue="orders-dlq" ttl="86400000" />

      <!-- Purge messages -->
      <q:queue name="temp-queue" action="purge" />

      <!-- Get queue info -->
      <q:queue name="orders" action="info" result="queueInfo" />
    """
    name: str = ""
    action: str = 'declare'  # declare, purge, delete, info
    durable: bool = True
    exclusive: bool = False
    auto_delete: bool = False
    dead_letter_queue: Optional[str] = None
    ttl: Optional[int] = None  # message TTL in ms
    result: Optional[str] = None  # for info action

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "queue",
            "name": self.name,
            "action": self.action,
            "durable": self.durable,
            "exclusive": self.exclusive,
            "auto_delete": self.auto_delete,
            "dead_letter_queue": self.dead_letter_queue,
            "ttl": self.ttl,
            "result": self.result
        }

    def validate(self) -> List[str]:
        errors = []

        if not self.name:
            errors.append("Queue requires 'name' attribute")

        if self.action not in ['declare', 'purge', 'delete', 'info']:
            errors.append(f"Invalid queue action: {self.action}. Must be declare, purge, delete, or info")

        if self.action == 'info' and not self.result:
            errors.append("Queue 'info' action requires 'result' attribute")

        if self.ttl is not None and self.ttl < 0:
            errors.append(f"TTL must be non-negative (got {self.ttl})")

        return errors

    def __repr__(self):
        return f'<QueueNode name={self.name} action={self.action}>'


@dataclass
class MessageAckNode(QuantumNode):
    """
    Represents message acknowledgment (q:messageAck).

    Used inside q:subscribe with ack="manual" to acknowledge
    successful message processing.

    Example:
      <q:subscribe name="worker" queue="tasks" ack="manual">
        <q:onMessage>
          <!-- Process message -->
          <q:set name="processed" value="true" />
          <!-- Acknowledge on success -->
          <q:messageAck />
        </q:onMessage>
      </q:subscribe>
    """

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "message_ack"
        }

    def validate(self) -> List[str]:
        return []

    def __repr__(self):
        return '<MessageAckNode>'


@dataclass
class MessageNackNode(QuantumNode):
    """
    Represents negative message acknowledgment (q:messageNack).

    Used inside q:subscribe with ack="manual" to reject a message.
    The requeue attribute controls whether the message is requeued.

    Examples:
      <!-- Reject and requeue (for retry) -->
      <q:messageNack requeue="true" />

      <!-- Reject without requeue (send to DLQ if configured) -->
      <q:messageNack requeue="false" />
    """
    requeue: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "message_nack",
            "requeue": self.requeue
        }

    def validate(self) -> List[str]:
        return []

    def __repr__(self):
        return f'<MessageNackNode requeue={self.requeue}>'


# =============================================================================
# Python Scripting Nodes (q:python, q:pyimport, q:class, q:decorator)
# =============================================================================

@dataclass
class PythonNode(QuantumNode):
    """
    Represents a Python code block (q:python).

    Allows embedding native Python code within Quantum components.
    The 'q' bridge object provides access to the Quantum context.

    Attributes:
        code: The Python code to execute
        scope: Variable scope ('component', 'isolated', 'module')
        async_mode: Whether to execute as async code
        timeout: Maximum execution time (e.g., '30s')
        result: Variable name to store the result

    Examples:
      <!-- Simple Python block -->
      <q:python>
          import pandas as pd
          df = pd.read_csv('data.csv')
          q.total = df['sales'].sum()
      </q:python>

      <!-- Async execution -->
      <q:python async="true" timeout="30s">
          import aiohttp
          async with aiohttp.ClientSession() as session:
              response = await session.get(url)
              q.data = await response.json()
      </q:python>

      <!-- Isolated scope (variables don't leak) -->
      <q:python scope="isolated">
          temp = calculate_something()
          q.export('result', temp)
      </q:python>

      <!-- With result capture -->
      <q:python result="calculation">
          return sum([1, 2, 3, 4, 5])
      </q:python>
    """
    code: str
    scope: str = "component"  # component, isolated, module
    async_mode: bool = False
    timeout: Optional[str] = None
    result: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "python",
            "code": self.code,
            "scope": self.scope,
            "async": self.async_mode,
            "timeout": self.timeout,
            "result": self.result
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.code or not self.code.strip():
            errors.append("Python code block cannot be empty")
        if self.scope not in ('component', 'isolated', 'module'):
            errors.append(f"Invalid scope: {self.scope}. Must be 'component', 'isolated', or 'module'")
        return errors

    def __repr__(self):
        code_preview = self.code[:50] + '...' if len(self.code) > 50 else self.code
        return f'<PythonNode scope={self.scope} code="{code_preview}">'


@dataclass
class PyImportNode(QuantumNode):
    """
    Represents a Python module import (q:pyimport).

    Imports Python modules into the component's namespace for use
    in q:python blocks and expressions.

    Attributes:
        module: The module to import (e.g., 'pandas', 'sklearn.ensemble')
        alias: Optional alias (e.g., 'pd' for pandas)
        names: Specific names to import from the module

    Examples:
      <!-- Import with alias -->
      <q:pyimport module="pandas" as="pd" />
      <q:pyimport module="numpy" as="np" />

      <!-- Import specific names -->
      <q:pyimport module="sklearn.ensemble" names="RandomForestClassifier, GradientBoostingClassifier" />

      <!-- Import everything from module -->
      <q:pyimport module="math" names="*" />

      <!-- Simple import -->
      <q:pyimport module="json" />
    """
    module: str
    alias: Optional[str] = None
    names: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "pyimport",
            "module": self.module,
            "alias": self.alias,
            "names": self.names
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.module:
            errors.append("Module name is required for q:pyimport")
        if self.alias and self.names:
            errors.append("Cannot use both 'as' and 'names' in the same import")
        return errors

    def __repr__(self):
        if self.alias:
            return f'<PyImportNode module={self.module} as={self.alias}>'
        elif self.names:
            return f'<PyImportNode from={self.module} names={self.names}>'
        return f'<PyImportNode module={self.module}>'


@dataclass
class PyClassNode(QuantumNode):
    """
    Represents an inline Python class definition (q:class).

    Allows defining Python classes within Quantum components.

    Attributes:
        name: The class name
        code: The class body (methods, attributes)
        bases: Base classes to inherit from
        decorators: Decorators to apply to the class

    Examples:
      <q:class name="OrderProcessor">
          def __init__(self, db):
              self.db = db

          def process(self, order_id):
              order = self.db.get(order_id)
              return self.validate(order)

          def validate(self, order):
              return order.total > 0
      </q:class>

      <!-- With inheritance -->
      <q:class name="AdminUser" bases="User, Permissions">
          role = 'admin'

          def has_permission(self, perm):
              return True
      </q:class>
    """
    name: str
    code: str
    bases: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "pyclass",
            "name": self.name,
            "code": self.code,
            "bases": self.bases,
            "decorators": self.decorators
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Class name is required for q:class")
        if not self.name.isidentifier():
            errors.append(f"Invalid class name: {self.name}")
        return errors

    def __repr__(self):
        bases_str = f"({', '.join(self.bases)})" if self.bases else ""
        return f'<PyClassNode name={self.name}{bases_str}>'


@dataclass
class PyDecoratorNode(QuantumNode):
    """
    Represents a Python decorator definition (q:decorator).

    Allows defining reusable decorators for functions.

    Attributes:
        name: The decorator name
        code: The decorator implementation
        params: Parameters the decorator accepts

    Examples:
      <!-- Caching decorator -->
      <q:decorator name="cached" params="ttl">
          from functools import wraps
          def decorator(func):
              cache = {}
              @wraps(func)
              def wrapper(*args):
                  if args in cache:
                      return cache[args]
                  result = func(*args)
                  cache[args] = result
                  return result
              return wrapper
          return decorator
      </q:decorator>

      <!-- Logging decorator -->
      <q:decorator name="logged">
          import logging
          def decorator(func):
              def wrapper(*args, **kwargs):
                  logging.info(f"Calling {func.__name__}")
                  return func(*args, **kwargs)
              return wrapper
          return decorator
      </q:decorator>
    """
    name: str
    code: str
    params: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "pydecorator",
            "name": self.name,
            "code": self.code,
            "params": self.params
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Decorator name is required")
        if not self.name.isidentifier():
            errors.append(f"Invalid decorator name: {self.name}")
        return errors

    def __repr__(self):
        return f'<PyDecoratorNode name={self.name}>'


@dataclass
class PyExprNode(QuantumNode):
    """
    Represents an inline Python expression (q:expr or {py: ...}).

    Used for embedding Python expressions within templates and attributes.

    Attributes:
        expr: The Python expression to evaluate
        format_spec: Optional format specification

    Examples:
      <!-- In attributes -->
      <q:set name="total" value="{py: sum(items)}" />

      <!-- With formatting -->
      <span>{py: price * 1.1:.2f}</span>

      <!-- List comprehension -->
      <q:set name="adults" value="{py: [u for u in users if u.age >= 18]}" />

      <!-- Ternary expression -->
      <span class="{py: 'active' if is_active else 'inactive'}">Status</span>
    """
    expr: str
    format_spec: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "pyexpr",
            "expr": self.expr,
            "format_spec": self.format_spec
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.expr or not self.expr.strip():
            errors.append("Python expression cannot be empty")
        return errors

    def __repr__(self):
        return f'<PyExprNode expr="{self.expr}">'
