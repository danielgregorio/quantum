"""
Quantum Component Runtime - Execute Quantum components
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

# Fix imports

from quantum.core.ast_nodes import (
    ComponentNode, QuantumReturn, DispatchEventNode, OnEventNode, QueryNode,
    DataNode, FileNode, MailNode, TransactionNode, LLMNode, LLMMessageNode,
    JobNode, ScheduleNode, ThreadNode,  # Job Execution System
    # Message Queue System
    MessageNode, SubscribeNode, QueueNode, MessageAckNode, MessageNackNode,
    # Python Scripting System
    PythonNode, PyImportNode, PyClassNode, PyDecoratorNode, PyExprNode,
    # Render-only nodes (handled by renderer, not executors)
    HTMLNode, TextNode, DocTypeNode,
    # Special-purpose nodes (handled outside executor dispatch)
    ActionNode, RedirectNode, FlashNode, CommentNode, ImportNode, SlotNode,
    ComponentCallNode,
)
from quantum.core.expression_diagnostics import is_absent_scope, report_unresolved
from quantum.core.expressions import (
    ExpressionEvaluator, ExpressionError, is_regex_quantifier,
)
from quantum.core.features.conditionals.src.ast_node import IfNode
from quantum.core.features.loops.src.ast_node import LoopNode
from quantum.core.features.state_management.src.ast_node import SetNode
from quantum.core.features.functions.src.ast_node import FunctionNode
from quantum.core.features.invocation.src.ast_node import InvokeNode
from quantum.core.features.knowledge_base.src.ast_node import KnowledgeNode
from quantum.core.features.agents.src.ast_node import AgentNode, AgentTeamNode
from quantum.core.features.websocket.src import (
    WebSocketNode, WebSocketHandlerNode, WebSocketSendNode, WebSocketCloseNode
)
from quantum.core.features.logging.src import LogNode, LoggingService
from quantum.core.features.dump.src import DumpNode, DumpService
from quantum.runtime.database_service import DatabaseService, QueryResult
from quantum.runtime.query_validators import QueryValidator, QueryValidationError
from quantum.runtime.execution_context import ExecutionContext, VariableNotFoundError
from quantum.runtime import param_validation
from quantum.runtime.validators import QuantumValidators, ValidationError
from quantum.runtime.function_registry import FunctionRegistry
from quantum.core.features.invocation.src.runtime import InvocationService
from quantum.core.features.data_import.src.runtime import DataImportService
from quantum.runtime.file_upload_service import FileUploadService, FileUploadError
from quantum.runtime.email_service import EmailService, EmailError
from quantum.runtime.llm_service import LLMService, LLMError
from quantum.runtime.knowledge_service import KnowledgeService, KnowledgeError
from quantum.runtime.agent_service import (
    AgentService, AgentError, get_agent_service,
    get_multi_agent_service, MultiAgentService, BUILTIN_TOOLS
)
from quantum.runtime.message_queue_service import MessageQueueService, MessageQueueError
from quantum.runtime.job_executor import (
    JobExecutor, ScheduleService, ThreadService, JobQueueService,
    JobExecutorError, ScheduleError, ThreadError, JobQueueError,
    parse_duration
)
from quantum.runtime.expression_cache import get_databinding_cache, DataBindingCache
from quantum.runtime.executor_registry import ExecutorRegistry
from quantum.runtime.service_container import ServiceContainer
import re
import logging

logger = logging.getLogger(__name__)


class ComponentExecutionError(Exception):
    """Error in component execution"""
    pass


def _create_executor_registry(runtime: 'ComponentRuntime') -> ExecutorRegistry:
    """
    Create and populate the executor registry with all executors.

    This factory function creates all modular executors and registers them.
    The registry can then dispatch execution to the appropriate executor
    based on node type.

    Args:
        runtime: ComponentRuntime instance for executor initialization

    Returns:
        Populated ExecutorRegistry
    """
    from quantum.runtime.executors import (
        # Control flow
        IfExecutor, LoopExecutor, SetExecutor,
        # Data
        QueryExecutor, InvokeExecutor, DataExecutor, TransactionExecutor,
        # Services
        LogExecutor, DumpExecutor, FileExecutor, MailExecutor,
        # AI
        LLMExecutor, AgentExecutor, TeamExecutor, KnowledgeExecutor,
        # Messaging
        WebSocketExecutor, WebSocketSendExecutor, WebSocketCloseExecutor,
        MessageExecutor, SubscribeExecutor, QueueExecutor,
        MessageAckExecutor, MessageNackExecutor,
        # Jobs
        ScheduleExecutor, ThreadExecutor, JobExecutor,
        # Scripting
        PythonExecutor, PyImportExecutor, PyClassExecutor,
    )

    registry = ExecutorRegistry()

    # Register all executors
    executors = [
        # Control flow
        IfExecutor(runtime),
        LoopExecutor(runtime),
        SetExecutor(runtime),
        # Data
        QueryExecutor(runtime),
        InvokeExecutor(runtime),
        DataExecutor(runtime),
        TransactionExecutor(runtime),
        # Services
        LogExecutor(runtime),
        DumpExecutor(runtime),
        FileExecutor(runtime),
        MailExecutor(runtime),
        # AI
        LLMExecutor(runtime),
        AgentExecutor(runtime),
        TeamExecutor(runtime),
        KnowledgeExecutor(runtime),
        # Messaging
        WebSocketExecutor(runtime),
        WebSocketSendExecutor(runtime),
        WebSocketCloseExecutor(runtime),
        MessageExecutor(runtime),
        SubscribeExecutor(runtime),
        QueueExecutor(runtime),
        MessageAckExecutor(runtime),
        MessageNackExecutor(runtime),
        # Jobs
        ScheduleExecutor(runtime),
        ThreadExecutor(runtime),
        JobExecutor(runtime),
        # Scripting
        PythonExecutor(runtime),
        PyImportExecutor(runtime),
        PyClassExecutor(runtime),
    ]

    registry.register_all(executors)
    logger.debug(f"Initialized executor registry with {registry.executor_count} executors")

    return registry

class ComponentRuntime:
    """Runtime for executing Quantum components"""

    def __init__(self, config: Dict[str, Any] = None, use_modular_executors: bool = True):
        self.execution_context = ExecutionContext()
        # Keep self.context for backward compatibility
        self.context: Dict[str, Any] = {}
        # Function registry
        self.function_registry = FunctionRegistry()
        # Current component (for function resolution)
        self.current_component: ComponentNode = None

        # === NEW: Service Container for dependency injection ===
        self._services = ServiceContainer(config)

        # === NEW: Executor Registry for modular dispatch ===
        self._use_modular_executors = use_modular_executors
        self._executor_registry: ExecutorRegistry = None
        if use_modular_executors:
            self._executor_registry = _create_executor_registry(self)
        else:
            import warnings
            warnings.warn(
                "use_modular_executors=False is deprecated and will be removed in v2.0. "
                "The modular ExecutorRegistry is now the default.",
                DeprecationWarning,
                stacklevel=2
            )

        # === LEGACY: Direct service references for backward compatibility ===
        # Database service for query execution - pass local datasources from config
        local_ds = {}
        if config and 'datasources' in config:
            local_ds = config['datasources']
        self.database_service = DatabaseService(local_datasources=local_ds)
        # Invocation service for q:invoke
        self.invocation_service = InvocationService()
        # Data import service for q:data
        self.data_import_service = DataImportService()
        # Logging service for q:log
        self.logging_service = LoggingService()
        # Dump service for q:dump
        self.dump_service = DumpService()
        # File upload service for q:file (Phase H)
        self.file_upload_service = FileUploadService()
        # Email service for q:mail (Phase I)
        self.email_service = EmailService()
        # LLM service for q:llm (Ollama backend)
        self.llm_service = LLMService()
        # Knowledge service for q:knowledge (RAG with ChromaDB)
        self.knowledge_service = KnowledgeService(self.llm_service)
        # Message queue service for q:message, q:subscribe, q:queue
        mq_config = {}
        if config and 'message_queue' in config:
            mq_config = config['message_queue']
        self.message_queue_service = MessageQueueService(mq_config)
        # Job executor for q:schedule, q:thread, q:job
        job_db_path = "quantum_jobs.db"
        if config and 'job_db_path' in config:
            job_db_path = config['job_db_path']
        max_thread_workers = 10
        if config and 'max_thread_workers' in config:
            max_thread_workers = config['max_thread_workers']
        self.job_executor = JobExecutor(
            max_thread_workers=max_thread_workers,
            job_db_path=job_db_path
        )
        # The one expression evaluator (FRAMEWORK_PLAN.md Fase 2.1). Nothing
        # else in this class compiles or executes an expression any more —
        # ExpressionCache's compile()+eval() is no longer reachable from the
        # runtime, which is the point.
        # function_resolver makes the component's own q:function callable from
        # an expression: {countElements(myArray)} used to resolve to nothing,
        # leaving the placeholder in the text for the surrounding q:set to
        # choke on ("could not convert string to float:
        # '{sumNumbers(myNumbers)}'"). The registry fills up while the
        # component executes, so it has to be a lookup, not a dict.
        self._expressions = ExpressionEvaluator(
            function_resolver=self._resolve_expression_function)
        # Databinding cache for optimized {variable} interpolation (Phase 1 enhancement)
        self._databinding_cache = get_databinding_cache()
        # Pre-compiled regex patterns (avoid re-compilation on every call)
        self._databinding_pattern = re.compile(r'\{([^}]+)\}')
        self._order_by_pattern = re.compile(r'\s+ORDER\s+BY\s+[^;]+?(?=\s+(?:LIMIT|OFFSET|FOR\s+UPDATE)|$)', re.IGNORECASE)
        self._limit_pattern = re.compile(r'\s+LIMIT\s+\d+', re.IGNORECASE)
        self._offset_pattern = re.compile(r'\s+OFFSET\s+\d+', re.IGNORECASE)

    @property
    def services(self) -> ServiceContainer:
        """Access to service container"""
        return self._services

    @property
    def executor_registry(self) -> ExecutorRegistry:
        """Access to executor registry (may be None if not using modular executors)"""
        return self._executor_registry

    def execute_component(self, component: ComponentNode, params: Dict[str, Any] = None) -> Any:
        """Execute a component and return the result"""
        if params is None:
            params = {}

        # Set current component
        self.current_component = component

        # Register component functions
        self.function_registry.register_component(component)

        # Phase F: Initialize scopes from special parameters before validation
        if '_session_scope' in params:
            self.execution_context.session_vars = params.pop('_session_scope')
        if '_application_scope' in params:
            self.execution_context.application_vars = params.pop('_application_scope')
        if '_request_scope' in params:
            self.execution_context.request_vars = params.pop('_request_scope')

        # Validate parameters
        validation_errors = self._validate_params(component, params)
        if validation_errors:
            raise ComponentExecutionError(f"Validation errors: {validation_errors}")

        # Setup context - add params to both contexts
        self.context.update(params)
        for key, value in params.items():
            self.execution_context.set_variable(key, value, scope="component")

        # Execute component
        try:
            # Execute control flow statements first
            for statement in component.statements:
                result = self._execute_statement(statement, self.execution_context)
                # Only return if the statement explicitly returns a value (not just executing)
                # SetNode returns None, LoopNode returns a list but shouldn't cause early return
                if result is not None and isinstance(statement, (IfNode,)):
                    # Only IfNode with a return statement should cause early return
                    return result

            # For now, simple execution based on q:return
            if component.returns:
                first_return = component.returns[0]
                # Use get_all_variables() for backward compatibility
                return self._process_return_value(first_return.value, self.execution_context.get_all_variables())

            return None

        except Exception as e:
            raise ComponentExecutionError(f"Execution error: {e}")
    
    def _validate_params(self, component: ComponentNode, params: Dict[str, Any]) -> List[str]:
        """Apply defaults, coerce types and check the rules on q:param.

        This used to check `required` and nothing else. The parser collects
        default, type, min, max, minlength, maxlength, pattern and enum from
        every q:param — and all of it was discarded, so

            <q:param name="idade" type="numeric" min="18" default="30" />

        left `idade` undefined ("{idade} did not resolve"), accepted the
        string "abc" as numeric, and accepted 7 for a minimum of 18. Every
        attribute but `required` was decoration.

        `params` is modified in place: defaults land in it, and values are
        replaced by their coerced form so the component sees a number where
        it asked for a number.
        """
        errors = []

        # getattr, not component.params: execute_component also runs
        # ApplicationNode (a q:application root), which declares no params and
        # raised AttributeError here — seven of the UI example tests failed
        # on this line, before reaching anything they were written to check.
        for param_def in getattr(component, 'params', None) or []:
            name = param_def.name
            if not name:
                continue

            if name not in params or params[name] is None:
                if param_def.default is not None:
                    params[name] = param_def.default
                elif param_def.required:
                    errors.append(f"Required parameter '{name}' is missing")
                    continue
                else:
                    continue

            value, error = self._coerce_param(param_def, params[name])
            if error:
                errors.append(error)
                continue
            params[name] = value

            errors.extend(self._check_param_rules(param_def, value))

        return errors

    def _coerce_param(self, param_def, value):
        """Return (coerced_value, error). Only for types with one meaning.

        Delega para quantum.runtime.param_validation: o ActionHandler tinha a
        propria copia desta logica, com outra lista de tipos e outro
        tratamento para arquivos, entao o mesmo q:param se comportava de dois
        jeitos conforme estivesse num componente ou num q:action.
        """
        return param_validation.coerce(param_def, value)

    def _check_param_rules(self, param_def, value) -> List[str]:
        """min/max/minlength/maxlength/pattern/enum."""
        return param_validation.check_rules(param_def, value)

    def _process_return_value(self, value: str, context: Dict[str, Any] = None) -> Any:
        """Process return value with databinding support"""
        if not value:
            return ""

        if context is None:
            context = {}

        # Apply databinding first
        processed_value = self._apply_databinding(value, context)

        # If databinding returned a non-string (e.g., int, float, dict), return it as-is
        if not isinstance(processed_value, str):
            return processed_value

        # Remove quotes if it's a string literal (after databinding)
        if processed_value.startswith('"') and processed_value.endswith('"'):
            return processed_value[1:-1]
        if processed_value.startswith("'") and processed_value.endswith("'"):
            return processed_value[1:-1]
        
        # Try to parse JSON
        if processed_value.startswith('{') or processed_value.startswith('['):
            try:
                import json
                return json.loads(processed_value)
            except:
                pass

        # Try to parse as number
        try:
            # Try int first
            if '.' not in processed_value:
                return int(processed_value)
            else:
                return float(processed_value)
        except (ValueError, AttributeError):
            # Not a number, return as string
            return processed_value
    
    def _execute_statement(self, statement, context):
        """Execute a control flow statement"""
        # Accept both ExecutionContext and Dict for backward compatibility
        if isinstance(context, ExecutionContext):
            exec_context = context
            dict_context = context.get_all_variables()
        else:
            exec_context = self.execution_context
            dict_context = context

        # Skip render-only and special-purpose nodes
        # HTMLNode/TextNode/DocTypeNode: handled by HTMLRenderer
        # ActionNode/RedirectNode/FlashNode: handled by ActionHandler
        # ImportNode: handled at load-time by ComponentResolver
        # SlotNode: handled by ComponentComposer
        # FunctionNode: registered in FunctionRegistry before execution
        # CommentNode: rendered as HTML comment by renderer
        if isinstance(statement, (
            HTMLNode, TextNode, DocTypeNode,
            ActionNode, RedirectNode, FlashNode,
            CommentNode, ImportNode, SlotNode, FunctionNode,
            # Resolved by HTMLRenderer._render_component_call during the render
            # pass, exactly like HTMLNode. It was missing from this list, so
            # every page using component composition — <Layout>, <Card> —
            # raised "No modular executor registered for ComponentCallNode"
            # and served a 500 the moment the legacy if-elif chain that used to
            # swallow it was removed.
            ComponentCallNode,
        )):
            return None

        # <q:return> aninhado dentro de q:if / q:else / q:loop. Nao tem
        # executor proprio: o nivel de componente coleta os returns a parte,
        # entao um return dentro de um corpo chegava aqui e explodia com "No
        # modular executor registered". Antes de o parser passar a reconhecer
        # o aninhamento, ele nem chegava — era descartado em silencio, e
        # `<q:if><q:return value="X"/></q:if>` simplesmente nao retornava X.
        if isinstance(statement, QuantumReturn):
            return self._process_return_value(statement.value, dict_context)

        # === MODULAR EXECUTOR REGISTRY (no fallback) ===
        if self._use_modular_executors and self._executor_registry:
            if self._executor_registry.can_execute(statement):
                return self._executor_registry.execute(statement, exec_context)
            else:
                # No executor registered for this node type
                node_type = type(statement).__name__
                raise ComponentExecutionError(f"No modular executor registered for {node_type}")

        # If modular executors are disabled, raise an error
        raise ComponentExecutionError("Modular executors are disabled but legacy fallback has been removed")

    def _execute_body(self, statements: List, context: Dict[str, Any]):
        """Execute a list of statements"""
        for statement in statements:
            if isinstance(statement, QuantumReturn):
                return self._process_return_value(statement.value, context)
            else:
                # Delegate to _execute_statement for all other types
                # (SetNode, IfNode, LoopNode, QueryNode, etc.)
                result = self._execute_statement(statement, self.execution_context)
                if result is not None and isinstance(statement, IfNode):
                    return result
        return None
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition string using databinding"""
        if not condition:
            return False

        # Evaluate the condition as an expression, without interpolating any
        # values into it first. Stripping the braces leaves the variable NAMES
        # in place for the evaluator to resolve, so no value is ever parsed as
        # syntax — unlike the databinding-then-evaluate path below, which
        # assembles code out of data. Same change as HTMLRenderer.
        stripped = self._databinding_pattern.sub(lambda m: m.group(1), condition).strip()

        # A regex quantifier as a whole condition is meaningless; false.
        if is_regex_quantifier(stripped):
            return False

        try:
            return bool(self._expressions.evaluate(stripped, context or {}))
        except ExpressionError:
            # A condition that could not be evaluated is FALSE.
            #
            # It used to fall through to a chain that interpolated the variable
            # VALUES into the text and took the truthiness of the result. For a
            # condition like `session.user.is_admin` on a logged-out request
            # that produced the literal string 'session.user.is_admin', which
            # is non-empty and therefore truthy — so the q:if fired its admin
            # branch and its q:else never did. A condition failing open is an
            # authorization bypass by construction. Reported by two audit
            # dimensions, reproduced directly, and the same fix as HTMLRenderer.
            #
            # That fallback chain also fed ExpressionCache's compile()+eval(),
            # whose regex denylist is bypassable by splitting a dunder across
            # adjacent string literals — so removing it closes a latent RCE
            # path as well as the fail-open.
            report_unresolved(stripped, ExpressionError(
                f"condition {condition!r} could not be evaluated; treated as false"
            ))
            return False

    def _apply_databinding(self, text: str, context: Dict[str, Any]) -> Any:
        """Apply variable databinding to text using {variable} syntax.

        Optimized with pre-compiled regex pattern and DataBindingCache for
        improved performance on repeated evaluations.
        """
        if not text:
            return text

        # Even if context is empty, we still need to process function calls
        if context is None:
            context = {}

        # Use pre-compiled pattern (avoid re-compilation on every call)
        pattern = self._databinding_pattern

        # Check if the ENTIRE text is just a single databinding expression
        full_match = pattern.fullmatch(text.strip())
        if full_match:
            # Pure expression - return the actual value (not converted to string)
            var_expr = full_match.group(1).strip()
            try:
                return self._evaluate_databinding_expression(var_expr, context)
            except Exception as exc:
                report_unresolved(var_expr, exc)
                # If evaluation fails, return original placeholder
                return text

        # Mixed content (text + expressions) - need string interpolation
        def replace_variable(match):
            var_expr = match.group(1).strip()
            try:
                result = self._evaluate_databinding_expression(var_expr, context)
                return str(result)
            except Exception as exc:
                report_unresolved(var_expr, exc)
                # If evaluation fails, return original placeholder
                return match.group(0)

        # Replace all {variable} patterns using pre-compiled pattern
        result = pattern.sub(replace_variable, text)
        return result
    
    def _evaluate_databinding_expression(self, expr: str, context: Dict[str, Any]) -> Any:
        """Evaluate a databinding expression like 'variable' or 'user.name' or 'functionName(args)' or 'result[0].id'

        The AST-whitelist evaluator (quantum.core.expressions) handles this now.
        Two things still route around it, and both are deliberate:

        - `q:function` calls, which need the FunctionRegistry, named-argument
          mapping and nested component resolution the legacy path implements.
        - Scoped variables (session., application., request., form., ...),
          whose contract is to resolve to '' when absent rather than to fail.

        Anything the evaluator refuses raises, and _apply_databinding turns
        that into the original placeholder — the same failure mode the engine
        always had.

        There was a fallback chain here during the migration. It was measured
        rather than judged: across pytest's declared testpaths it took 863
        calls over 434 distinct expressions and failed all 863 — not one
        expression it could resolve that the evaluator could not. It was
        deleted rather than kept as reassurance, because two grammars that
        disagree is the problem this phase set out to remove.

        (The commit that deleted it says "73 calls, 73 failures". That figure
        came from `pytest tests/`, which is a subset of the `testpaths` in
        pytest.ini. The load-bearing half — zero resolved — holds under every
        scope measured; the count does not.)
        """
        # Regex quantifiers are not expressions. See is_regex_quantifier().
        if is_regex_quantifier(expr):
            raise ValueError(f"'{expr}' is a regex quantifier, not an expression")

        # Isto desviava para _evaluate_function_call qualquer expressao que
        # COMECASSE com uma chamada de q:function — e la o regex
        # `(\w+)\((.*)\)` pega tudo ate o ultimo parentese e ignora o
        # resto. `{dobro(a) * 10}` devolvia 10 em vez de 100: o `* 10` era
        # descartado em silencio. `10 * dobro(a)` funcionava, porque nao
        # comecava com a chamada — a mesma conta dava resultados diferentes
        # conforme a ordem dos fatores.
        #
        # O avaliador ja resolve q:function pelo function_resolver e compoe
        # com aritmetica corretamente, entao o desvio nao e mais necessario.
        # Conferido: dobro(a), dobro(a) * 10, dobro(a) + dobro(a) e
        # 10 * dobro(a) dao 10, 100, 20 e 100.

        try:
            return self._expressions.evaluate(expr, context)
        except ExpressionError as exc:
            # Scoped variables resolve to '' when absent, matching
            # get_variable()'s default: templates render before login. Shared
            # with HTMLRenderer so both passes agree.
            if is_absent_scope(expr):
                return ''
            raise ValueError(str(exc)) from exc

    def _evaluate_function_call(self, expr: str, context: Dict[str, Any]) -> Any:
        """
        Evaluate function call expression like 'add(5, 3)' or 'calculateTotal(items, 0.1)'
        """
        # Parse function name and arguments
        match = re.match(r'(\w+)\((.*)\)', expr.strip())
        if not match:
            raise ComponentExecutionError(f"Invalid function call syntax: {expr}")

        func_name = match.group(1)
        args_str = match.group(2).strip()

        # Resolve function
        func_node = self.function_registry.resolve_function(func_name, self.current_component)
        if not func_node:
            raise ComponentExecutionError(f"Function '{func_name}' not found")

        # Parse arguments
        args = self._parse_function_arguments(args_str, context, func_node)

        # Execute function
        return self._execute_function(func_node, args)

    def _parse_function_arguments(self, args_str: str, context: Dict[str, Any], func_node: FunctionNode) -> Dict[str, Any]:
        """Parse function arguments from string like '5, 3' or 'items, 0.1' or 'add(2, 3), 4'"""
        if not args_str:
            return {}

        # Smart split by comma - respect nested parentheses
        args = self._smart_split_args(args_str)

        arg_values = []
        for arg in args:
            arg = arg.strip()

            # Evaluate each argument as an expression
            try:
                # Try to evaluate as databinding expression (handles nested function calls)
                value = self._evaluate_databinding_expression(arg, context)
                arg_values.append(value)
            except:
                # Fallback: try as literal
                try:
                    # Try to parse as number
                    if '.' in arg:
                        arg_values.append(float(arg))
                    else:
                        arg_values.append(int(arg))
                except:
                    # Use as string (remove quotes if present)
                    if arg.startswith('\"') and arg.endswith('\"'):
                        arg_values.append(arg[1:-1])
                    elif arg.startswith("'") and arg.endswith("'"):
                        arg_values.append(arg[1:-1])
                    else:
                        arg_values.append(arg)

        # Match positional args to parameter names
        return dict(zip([p.name for p in func_node.params], arg_values))

    def _smart_split_args(self, args_str: str) -> List[str]:
        """Split arguments by comma, respecting nested parentheses"""
        args = []
        current_arg = []
        paren_depth = 0

        for char in args_str:
            if char == '(':
                paren_depth += 1
                current_arg.append(char)
            elif char == ')':
                paren_depth -= 1
                current_arg.append(char)
            elif char == ',' and paren_depth == 0:
                # Top-level comma - split here
                args.append(''.join(current_arg))
                current_arg = []
            else:
                current_arg.append(char)

        # Add last argument
        if current_arg:
            args.append(''.join(current_arg))

        return args

    # -- the interface InvocationService expects -------------------------
    #
    # q:invoke function="..." routed through InvocationService, which calls
    # context.get_function(name) and context.execute_function(name, args) on
    # whatever it is handed — and it is handed this runtime, which had
    # neither method. So the service returned
    # "Context does not support function invocation" and q:invoke silently
    # produced nothing. The tenth instance of this project's recurring
    # pattern: a service written against an imagined interface, with the
    # tests mocking that same imagination.
    #
    # Implemented against the real FunctionRegistry rather than rewriting
    # the service, because the interface it assumed is a reasonable one.

    def get_function(self, name: str):
        """The FunctionNode for `name`, or None."""
        return self.function_registry.resolve_function(name, self.current_component)

    def _resolve_expression_function(self, name: str):
        """Wrap a q:function so an expression can call it positionally.

        `{somaTotal(itens)}` passes arguments by position; q:function binds
        them by parameter name, so they are zipped against the declared
        params — the same rule q:invoke uses.
        """
        func_node = self.get_function(name)
        if not func_node:
            return None

        def call(*args, **kwargs):
            bound = dict(zip([p.name for p in func_node.params], args))
            bound.update(kwargs)
            return self._execute_function(func_node, bound)

        call.__name__ = name
        return call

    def execute_function(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a q:function by name. Returns the service's result shape."""
        func_node = self.get_function(name)
        if not func_node:
            return {'success': False, 'error': f"Function '{name}' not found"}
        try:
            return {'success': True, 'data': self._execute_function(func_node, args or {})}
        except Exception as exc:  # noqa: BLE001
            logger.exception("q:invoke function=%r failed", name)
            return {'success': False, 'error': str(exc)}

    def _execute_function(self, func_node: FunctionNode, args: Dict[str, Any]) -> Any:
        """Execute function with given arguments"""

        # Validate function parameters if requested
        if func_node.validate_params:
            self._validate_function_args(func_node, args)

        # Create function execution context (child of current context)
        func_context = self.execution_context.create_child_context()

        # Bind parameters to context
        for param in func_node.params:
            value = args.get(param.name)

            # Use default if not provided
            if value is None and param.default is not None:
                value = param.default

            # Check required
            if param.required and value is None:
                raise ComponentExecutionError(f"Required parameter '{param.name}' not provided")

            # Set in function context
            func_context.set_variable(param.name, value, scope="local")

        # Execute function body using modular executors.
        #
        # The context is swapped, not just passed. BaseExecutor.context is
        # `self._runtime.execution_context` and get_all_variables() reads it,
        # so every executor in the body looked at the COMPONENT's variables
        # and never at the function's — a q:function could not see its own
        # parameters. `<q:loop items="{numbers}">` inside a function whose
        # parameter is `numbers` failed with "variable 'numbers' is not
        # defined, did you mean 'myNumbers'?", naming the caller's variable.
        previous_context = self.execution_context
        self.execution_context = func_context
        try:
            result = None
            for statement in func_node.body:
                if isinstance(statement, QuantumReturn):
                    # Evaluate return value
                    result = self._process_return_value(
                        statement.value, func_context.get_all_variables())
                    break
                else:
                    # Delegate all other statements to the executor registry
                    result = self._execute_statement(statement, func_context)
                    if result is not None and isinstance(statement, IfNode):
                        break
        finally:
            self.execution_context = previous_context

        return result

    def _validate_function_args(self, func_node: FunctionNode, args: Dict[str, Any]):
        """Validate function arguments against parameter definitions"""
        for param in func_node.params:
            value = args.get(param.name)

            # Check required
            if param.required and value is None:
                raise ComponentExecutionError(f"Required parameter '{param.name}' is missing")

            # Skip validation if no value provided
            if value is None:
                continue

            # Validate using QuantumValidators
            if param.validate_rule:
                # Use the generic validate method for all rules
                is_valid, error = QuantumValidators.validate(value, param.validate_rule)
                if not is_valid:
                    raise ValidationError(f"Parameter '{param.name}': {error}")

            # Validate range
            if param.range:
                is_valid, error = QuantumValidators.validate_range(value, param.range)
                if not is_valid:
                    raise ValidationError(f"Parameter '{param.name}': {error}")

            # Validate enum
            if param.enum:
                is_valid, error = QuantumValidators.validate_enum(value, param.enum)
                if not is_valid:
                    raise ValidationError(f"Parameter '{param.name}': {error}")

    def _execute_dispatch_event(self, dispatch_node: DispatchEventNode, context: Dict[str, Any]):
        """Execute q:dispatchEvent statement"""
        # For now, just log the event (TODO: integrate with actual message queue)
        event_data = {
            'event': dispatch_node.event,
            'data': self._apply_databinding(dispatch_node.data, context) if dispatch_node.data else None,
            'queue': dispatch_node.queue,
            'priority': dispatch_node.priority,
        }

        print(f"[EVENT DISPATCHED] {event_data}")
        # TODO: Integrate with RabbitMQ/SQS/etc

    def _execute_on_event(self, event_node: OnEventNode, event_data: Dict[str, Any]):
        """Execute q:onEvent handler (called by event system)"""
        # Create event context
        event_context = self.execution_context.create_child_context(scope="local")

        # Add event data to context
        for key, value in event_data.items():
            event_context.set_variable(key, value, scope="local")

        # Execute event handler body using modular executors
        for statement in event_node.body:
            self._execute_statement(statement, event_context)

    def _execute_knowledge_query(self, query_node: QueryNode, resolved_params: dict, exec_context: ExecutionContext):
        """
        Execute a q:query against a knowledge: virtual datasource.

        Supports two modes:
        - Search mode (default): vector similarity search, returns [{content, relevance, source}]
        - RAG mode (mode="rag"): search + LLM answer, returns {answer, sources, confidence}

        Args:
            query_node: QueryNode with datasource="knowledge:{name}"
            resolved_params: Resolved query parameters
            exec_context: Execution context
        """
        from quantum.runtime.database_service import QueryResult

        try:
            # Extract knowledge base name from datasource
            kb_name = query_node.datasource.replace('knowledge:', '', 1)

            # Check if knowledge base failed to initialize - return empty results
            kb_meta = exec_context.get_variable(f"_knowledge_{kb_name}")
            if isinstance(kb_meta, dict) and kb_meta.get("_failed"):
                from quantum.runtime.database_service import QueryResult as _QR
                mode = query_node.mode
                if mode == 'rag':
                    empty_data = [{"answer": "Knowledge base is still loading. Please refresh the page.", "sources": "", "confidence": "0"}]
                    result = _QR(data=empty_data, column_list=['answer', 'sources', 'confidence'], execution_time=0.0, record_count=1, success=True)
                else:
                    result = _QR(data=[], column_list=['content', 'relevance', 'source', 'chunk_index'], execution_time=0.0, record_count=0, success=True)
                result_dict = result.to_dict()
                exec_context.set_variable(query_node.name, result.data, scope="component")
                exec_context.set_variable(f"{query_node.name}_result", result_dict, scope="component")
                self.context[query_node.name] = result.data
                self.context[f"{query_node.name}_result"] = result_dict
                if result.data and len(result.data) == 1 and isinstance(result.data[0], dict):
                    for field_name, field_value in result.data[0].items():
                        dotted_key = f"{query_node.name}.{field_name}"
                        exec_context.set_variable(dotted_key, field_value, scope="component")
                        self.context[dotted_key] = field_value
                return result

            # Get the search query from the first parameter value
            search_text = None
            for param_name, param_value in resolved_params.items():
                search_text = str(param_value)
                break

            if not search_text:
                raise KnowledgeError("Knowledge query requires at least one parameter for the search query")

            # Parse LIMIT from SQL if present
            n_results = 5
            limit_match = re.search(r'LIMIT\s+(\d+)', query_node.sql, re.IGNORECASE)
            if limit_match:
                n_results = int(limit_match.group(1))

            # Get embed model from knowledge base metadata
            embed_model = "nomic-embed-text"
            kb_model = None
            if isinstance(kb_meta, dict):
                embed_model = kb_meta.get("embed_model", embed_model)
                kb_model = kb_meta.get("model")

            # Determine mode
            mode = query_node.mode  # None or "rag"

            if mode == 'rag':
                # RAG mode: search + LLM answer
                rag_model = query_node.rag_model or kb_model
                result_data = self.knowledge_service.rag_query(
                    name=kb_name,
                    question=search_text,
                    model=rag_model,
                    n_results=n_results,
                    embed_model=embed_model,
                )

                # Store as single-row result for {name.field} access
                data = [result_data]
                result = QueryResult(
                    data=data,
                    column_list=['answer', 'sources', 'confidence'],
                    execution_time=0.0,
                    record_count=1,
                    success=True,
                )

            else:
                # Search mode: vector similarity
                search_results = self.knowledge_service.search(
                    name=kb_name,
                    query_text=search_text,
                    n_results=n_results,
                    embed_model=embed_model,
                )

                data = search_results
                result = QueryResult(
                    data=data,
                    column_list=['content', 'relevance', 'source', 'chunk_index'],
                    execution_time=0.0,
                    record_count=len(data),
                    success=True,
                )

            # Store results in context (same pattern as regular query)
            result_dict = result.to_dict()
            exec_context.set_variable(query_node.name, result.data, scope="component")
            exec_context.set_variable(f"{query_node.name}_result", result_dict, scope="component")
            self.context[query_node.name] = result.data
            self.context[f"{query_node.name}_result"] = result_dict

            # For single-row results, expose fields directly ({name.field})
            if result.data and len(result.data) == 1 and isinstance(result.data[0], dict):
                for field_name, field_value in result.data[0].items():
                    dotted_key = f"{query_node.name}.{field_name}"
                    exec_context.set_variable(dotted_key, field_value, scope="component")
                    self.context[dotted_key] = field_value

            if query_node.result:
                exec_context.set_variable(query_node.result, result_dict, scope="component")
                self.context[query_node.result] = result_dict

            return result

        except KnowledgeError as e:
            raise ComponentExecutionError(f"Knowledge query error in '{query_node.name}': {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Knowledge query execution error in '{query_node.name}': {e}")

    # ============================================
    # JOB EXECUTION SYSTEM (q:schedule, q:thread, q:job)
