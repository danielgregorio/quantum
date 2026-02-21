"""
Quantum Component Runtime - Execute Quantum components
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

# Fix imports
sys.path.append(str(Path(__file__).parent.parent))

from core.ast_nodes import (
    ComponentNode, QuantumReturn, DispatchEventNode, OnEventNode, QueryNode,
    DataNode, FileNode, MailNode, TransactionNode, LLMNode, LLMMessageNode,
    JobNode, ScheduleNode, ThreadNode,  # Job Execution System
    # Message Queue System
    MessageNode, SubscribeNode, QueueNode, MessageAckNode, MessageNackNode,
    # Python Scripting System
    PythonNode, PyImportNode, PyClassNode, PyDecoratorNode, PyExprNode
)
from core.features.conditionals.src.ast_node import IfNode
from core.features.loops.src.ast_node import LoopNode
from core.features.state_management.src.ast_node import SetNode
from core.features.functions.src.ast_node import FunctionNode
from core.features.invocation.src.ast_node import InvokeNode
from core.features.knowledge_base.src.ast_node import KnowledgeNode
from core.features.agents.src.ast_node import AgentNode, AgentTeamNode
from core.features.websocket.src import (
    WebSocketNode, WebSocketHandlerNode, WebSocketSendNode, WebSocketCloseNode
)
from core.features.logging.src import LogNode, LoggingService
from core.features.dump.src import DumpNode, DumpService
from runtime.database_service import DatabaseService, QueryResult
from runtime.query_validators import QueryValidator, QueryValidationError
from runtime.execution_context import ExecutionContext, VariableNotFoundError
from runtime.validators import QuantumValidators, ValidationError
from runtime.function_registry import FunctionRegistry
from core.features.invocation.src.runtime import InvocationService
from core.features.data_import.src.runtime import DataImportService
from runtime.file_upload_service import FileUploadService, FileUploadError
from runtime.email_service import EmailService, EmailError
from runtime.llm_service import LLMService, LLMError
from runtime.knowledge_service import KnowledgeService, KnowledgeError
from runtime.agent_service import (
    AgentService, AgentError, get_agent_service,
    get_multi_agent_service, MultiAgentService, BUILTIN_TOOLS
)
from runtime.message_queue_service import MessageQueueService, MessageQueueError
from runtime.job_executor import (
    JobExecutor, ScheduleService, ThreadService, JobQueueService,
    JobExecutorError, ScheduleError, ThreadError, JobQueueError,
    parse_duration
)
from runtime.expression_cache import get_expression_cache, ExpressionCache, get_databinding_cache, DataBindingCache
from runtime.executor_registry import ExecutorRegistry
from runtime.service_container import ServiceContainer
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
    from runtime.executors import (
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
        # Expression cache for performance optimization (Phase 1)
        self._expr_cache = get_expression_cache()
        # Databinding cache for optimized {variable} interpolation (Phase 1 enhancement)
        self._databinding_cache = get_databinding_cache()
        # Pre-compiled regex patterns (avoid re-compilation on every call)
        self._databinding_pattern = re.compile(r'\{([^}]+)\}')
        self._array_index_pattern = re.compile(r'^(\w+)\[(\d+)\](\.(.+))?$')
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
        """Validate component parameters"""
        errors = []
        
        for param_def in component.params:
            if param_def.required and param_def.name not in params:
                errors.append(f"Required parameter '{param_def.name}' is missing")
        
        return errors
    
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

        # === NEW: Try modular executor registry first ===
        if self._use_modular_executors and self._executor_registry:
            try:
                if self._executor_registry.can_execute(statement):
                    return self._executor_registry.execute(statement, exec_context)
            except Exception as e:
                # Log warning and fall back to legacy execution
                logger.warning(f"Modular executor failed for {type(statement).__name__}: {e}")

        # === LEGACY: Fall back to if-elif chain ===
        # DEPRECATION NOTE: This if-elif chain is deprecated and will be removed in v2.0
        # All node execution should go through the modular ExecutorRegistry
        node_type = type(statement).__name__
        logger.debug(f"LEGACY FALLBACK: Executing {node_type} via if-elif chain (deprecated)")

        if isinstance(statement, IfNode):
            return self._execute_if(statement, dict_context)
        elif isinstance(statement, LoopNode):
            return self._execute_loop(statement, dict_context)
        elif isinstance(statement, SetNode):
            return self._execute_set(statement, exec_context)
        elif isinstance(statement, QueryNode):
            return self._execute_query(statement, exec_context)
        elif isinstance(statement, InvokeNode):
            return self._execute_invoke(statement, exec_context)
        elif isinstance(statement, DataNode):
            return self._execute_data(statement, exec_context)
        elif isinstance(statement, LogNode):
            return self._execute_log(statement, exec_context)
        elif isinstance(statement, DumpNode):
            return self._execute_dump(statement, exec_context)
        elif isinstance(statement, FileNode):
            return self._execute_file(statement, exec_context)
        elif isinstance(statement, MailNode):
            return self._execute_mail(statement, exec_context)
        elif isinstance(statement, TransactionNode):
            return self._execute_transaction(statement, exec_context)
        elif isinstance(statement, LLMNode):
            return self._execute_llm(statement, exec_context)
        elif isinstance(statement, KnowledgeNode):
            return self._execute_knowledge(statement, exec_context)
        elif isinstance(statement, AgentNode):
            return self._execute_agent(statement, exec_context)
        elif isinstance(statement, AgentTeamNode):
            return self._execute_team(statement, exec_context)
        # WebSocket System
        elif isinstance(statement, WebSocketNode):
            return self._execute_websocket(statement, exec_context)
        elif isinstance(statement, WebSocketSendNode):
            return self._execute_websocket_send(statement, exec_context)
        elif isinstance(statement, WebSocketCloseNode):
            return self._execute_websocket_close(statement, exec_context)
        # Job Execution System
        elif isinstance(statement, ScheduleNode):
            return self._execute_schedule(statement, exec_context)
        elif isinstance(statement, ThreadNode):
            return self._execute_thread(statement, exec_context)
        elif isinstance(statement, JobNode):
            return self._execute_job(statement, exec_context)
        # Message Queue System
        elif isinstance(statement, MessageNode):
            return self._execute_message(statement, exec_context)
        elif isinstance(statement, SubscribeNode):
            return self._execute_subscribe(statement, exec_context)
        elif isinstance(statement, QueueNode):
            return self._execute_queue(statement, exec_context)
        elif isinstance(statement, MessageAckNode):
            return self._execute_message_ack(statement, exec_context)
        elif isinstance(statement, MessageNackNode):
            return self._execute_message_nack(statement, exec_context)
        # Python Scripting System
        elif isinstance(statement, PythonNode):
            return self._execute_python(statement, exec_context)
        elif isinstance(statement, PyImportNode):
            return self._execute_pyimport(statement, exec_context)
        elif isinstance(statement, PyClassNode):
            return self._execute_pyclass(statement, exec_context)
        elif isinstance(statement, PyDecoratorNode):
            return self._execute_pydecorator(statement, exec_context)
        return None

    def _execute_if(self, if_node: IfNode, context: Dict[str, Any]):
        """Execute q:if statement with elseif and else"""
        
        # Evaluate main if condition
        if self._evaluate_condition(if_node.condition, context):
            return self._execute_body(if_node.if_body, context)
        
        # Check elseif conditions
        for elseif_block in if_node.elseif_blocks:
            if self._evaluate_condition(elseif_block["condition"], context):
                return self._execute_body(elseif_block["body"], context)
        
        # Execute else block if present
        if if_node.else_body:
            return self._execute_body(if_node.else_body, context)
        
        return None
    
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

        try:
            # Check if this is a comparison expression with databinding
            # e.g., "{form.action_type} == 'logout'" or "{x} != 'hello'"
            comparison_ops = ['==', '!=', '>=', '<=', '>', '<']
            has_comparison = any(op in condition for op in comparison_ops)

            if has_comparison and '{' in condition:
                # Handle comparison expressions by evaluating each {expr} separately
                # and comparing the resolved values programmatically
                return self._evaluate_comparison_condition(condition, context, comparison_ops)

            # Apply databinding to resolve variables
            evaluated_condition = self._apply_databinding(condition, context)

            # If databinding returned a non-string type, use its truthiness directly
            if not isinstance(evaluated_condition, str):
                return bool(evaluated_condition)

            # If the result still contains unresolved {expressions}, treat as False
            if '{' in evaluated_condition:
                return False

            # Try to evaluate as a Python expression (handles: "3 > 1", "True", "1 == 1", etc.)
            try:
                # Use expression cache for faster evaluation
                return self._expr_cache.evaluate_condition(evaluated_condition, context)
            except (ValueError, RuntimeError):
                # Not a valid Python expression - treat as a plain resolved string
                # and use its truthiness (non-empty string = True, empty = False)
                return bool(evaluated_condition)
        except Exception as e:
            # Fallback - return False for safety
            return False

    def _evaluate_comparison_condition(self, condition: str, context: Dict[str, Any],
                                        comparison_ops: list) -> bool:
        """Evaluate a condition that contains both {databinding} and comparison operators.

        Resolves each side of the comparison separately and compares the actual values,
        avoiding the problem of unquoted string interpolation into eval().
        """
        # Find which comparison operator is used (check longest first to match >= before >)
        op = None
        op_pos = -1
        for candidate in sorted(comparison_ops, key=len, reverse=True):
            pos = condition.find(candidate)
            if pos != -1:
                # Make sure this isn't inside a {databinding} expression
                before = condition[:pos]
                if before.count('{') == before.count('}'):
                    op = candidate
                    op_pos = pos
                    break

        if op is None:
            return False

        left_str = condition[:op_pos].strip()
        right_str = condition[op_pos + len(op):].strip()

        # Resolve each side
        left_val = self._apply_databinding(left_str, context) if left_str else ''
        right_val = self._apply_databinding(right_str, context) if right_str else ''

        # Strip quotes from literal strings (e.g., "'logout'" -> "logout")
        if isinstance(right_val, str):
            right_val = right_val.strip()
            if (right_val.startswith("'") and right_val.endswith("'")) or \
               (right_val.startswith('"') and right_val.endswith('"')):
                right_val = right_val[1:-1]
        if isinstance(left_val, str):
            left_val = left_val.strip()
            if (left_val.startswith("'") and left_val.endswith("'")) or \
               (left_val.startswith('"') and left_val.endswith('"')):
                left_val = left_val[1:-1]

        # Perform comparison
        if op == '==':
            return left_val == right_val
        elif op == '!=':
            return left_val != right_val
        elif op in ('>', '<', '>=', '<='):
            try:
                left_num = float(left_val) if isinstance(left_val, str) else left_val
                right_num = float(right_val) if isinstance(right_val, str) else right_val
                if op == '>':
                    return left_num > right_num
                elif op == '<':
                    return left_num < right_num
                elif op == '>=':
                    return left_num >= right_num
                elif op == '<=':
                    return left_num <= right_num
            except (ValueError, TypeError):
                return str(left_val) > str(right_val) if op == '>' else \
                       str(left_val) < str(right_val) if op == '<' else \
                       str(left_val) >= str(right_val) if op == '>=' else \
                       str(left_val) <= str(right_val)
        return False
    
    def _execute_loop(self, loop_node: LoopNode, context: Dict[str, Any], exec_context: ExecutionContext = None):
        """Execute q:loop statement with various types"""
        # Use provided exec_context or fall back to component context
        if exec_context is None:
            exec_context = self.execution_context

        if loop_node.loop_type == 'range':
            return self._execute_range_loop(loop_node, context, exec_context)
        elif loop_node.loop_type == 'array':
            return self._execute_array_loop(loop_node, context, exec_context)
        elif loop_node.loop_type == 'list':
            return self._execute_list_loop(loop_node, context, exec_context)
        elif loop_node.loop_type == 'query':
            return self._execute_query_loop(loop_node, context, exec_context)
        else:
            raise ComponentExecutionError(f"Unsupported loop type: {loop_node.loop_type}")
    
    def _execute_range_loop(self, loop_node: LoopNode, context: Dict[str, Any], exec_context: ExecutionContext):
        """Execute range loop (from/to/step)"""
        results = []

        try:
            # Evaluate from and to values
            start = int(self._evaluate_simple_expression(loop_node.from_value, context))
            end = int(self._evaluate_simple_expression(loop_node.to_value, context))
            step = loop_node.step_value

            # Execute loop
            for i in range(start, end + 1, step):
                # Create loop context with loop variable
                loop_context = context.copy()
                loop_context[loop_node.var_name] = i

                # Also update execution context for q:set support
                exec_context.set_variable(loop_node.var_name, i, scope="local")

                # Execute loop body
                for statement in loop_node.body:
                    result = self._execute_loop_body_statement(statement, loop_context, exec_context)
                    if result is not None:
                        results.append(result)

            return results

        except (ValueError, TypeError) as e:
            raise ComponentExecutionError(f"Range loop error: {e}")
    
    def _execute_array_loop(self, loop_node: LoopNode, context: Dict[str, Any], exec_context: ExecutionContext):
        """Execute array loop"""
        results = []

        try:
            # Get array data (for now, parse simple array notation)
            array_data = self._parse_array_items(loop_node.items, context)

            # Execute loop
            for index, item in enumerate(array_data):
                # Set loop variable in execution context
                exec_context.set_variable(loop_node.var_name, item, scope="local")

                # Add index if specified
                if loop_node.index_name:
                    exec_context.set_variable(loop_node.index_name, index, scope="local")

                # Get fresh context dict from execution context (includes all updated variables)
                loop_context = exec_context.get_all_variables()

                # Execute loop body
                for statement in loop_node.body:
                    result = self._execute_loop_body_statement(statement, loop_context, exec_context)
                    if result is not None:
                        results.append(result)

                    # Sync loop_context after each statement to see updates
                    loop_context = exec_context.get_all_variables()

            return results

        except Exception as e:
            raise ComponentExecutionError(f"Array loop error: {e}")
    
    def _execute_list_loop(self, loop_node: LoopNode, context: Dict[str, Any], exec_context: ExecutionContext):
        """Execute list loop"""
        results = []

        try:
            # Get list data and split by delimiter
            list_data = self._parse_list_items(loop_node.items, loop_node.delimiter, context)

            # Execute loop
            for index, item in enumerate(list_data):
                # Create loop context with loop variable(s)
                loop_context = context.copy()
                loop_context[loop_node.var_name] = item.strip()

                # Also update execution context for q:set support
                exec_context.set_variable(loop_node.var_name, item.strip(), scope="local")

                # Add index if specified
                if loop_node.index_name:
                    loop_context[loop_node.index_name] = index
                    exec_context.set_variable(loop_node.index_name, index, scope="local")

                # Execute loop body
                for statement in loop_node.body:
                    result = self._execute_loop_body_statement(statement, loop_context, exec_context)
                    if result is not None:
                        results.append(result)

            return results

        except Exception as e:
            raise ComponentExecutionError(f"List loop error: {e}")

    def _execute_query_loop(self, loop_node: LoopNode, context: Dict[str, Any], exec_context: ExecutionContext):
        """Execute query loop - iterate over query result rows"""
        results = []

        try:
            # Get query data from context
            query_name = loop_node.query_name if hasattr(loop_node, 'query_name') else loop_node.var_name
            query_data = context.get(query_name)

            if query_data is None:
                # Try execution context
                query_data = exec_context.get_variable(query_name)

            if not query_data:
                raise ComponentExecutionError(f"Query '{query_name}' not found in context")

            if not isinstance(query_data, list):
                raise ComponentExecutionError(f"Query '{query_name}' is not iterable (got {type(query_data).__name__})")

            # Iterate over query rows
            for index, row in enumerate(query_data):
                # Create loop context with current row fields available as {queryName.fieldName}
                loop_context = context.copy()

                # Set current row index
                current_row_index = index

                # Make row fields accessible via dot notation and bare name
                # Store row data under query name for {queryName.field} access
                # Also store bare field names for ColdFusion-style {field} access inside loops
                if isinstance(row, dict):
                    for field_name, field_value in row.items():
                        # Set {queryName.fieldName} in context
                        dotted_key = f"{query_name}.{field_name}"
                        loop_context[dotted_key] = field_value
                        exec_context.set_variable(dotted_key, field_value, scope="local")
                        # Set bare {fieldName} for direct access inside query loops
                        loop_context[field_name] = field_value
                        exec_context.set_variable(field_name, field_value, scope="local")

                # Also provide currentRow variable for explicit access
                loop_context['currentRow'] = row
                exec_context.set_variable('currentRow', row, scope="local")

                # Provide index if requested
                if loop_node.index_name:
                    loop_context[loop_node.index_name] = index
                    exec_context.set_variable(loop_node.index_name, index, scope="local")

                # Execute loop body
                for statement in loop_node.body:
                    result = self._execute_loop_body_statement(statement, loop_context, exec_context)
                    if result is not None:
                        results.append(result)

            return results

        except Exception as e:
            raise ComponentExecutionError(f"Query loop error: {e}")

    def _execute_loop_body_statement(self, statement, context: Dict[str, Any], exec_context: ExecutionContext):
        """Execute a statement inside a loop body"""
        if isinstance(statement, QuantumReturn):
            return self._process_return_value(statement.value, context)
        elif isinstance(statement, IfNode):
            return self._execute_if(statement, context)
        elif isinstance(statement, LoopNode):
            return self._execute_loop(statement, context, exec_context)
        elif isinstance(statement, SetNode):
            # Execute set using the provided execution context
            return self._execute_set(statement, exec_context)
        elif isinstance(statement, LogNode):
            return self._execute_log(statement, exec_context)
        elif isinstance(statement, DumpNode):
            return self._execute_dump(statement, exec_context)
        return None
    
    def _evaluate_simple_expression(self, expr: str, context: Dict[str, Any]) -> Any:
        """Basic expression evaluation for simple values"""
        if not expr:
            return 0
        
        # For now, just handle simple numeric values
        # TODO: Expand to handle variables and complex expressions
        try:
            return int(expr)
        except ValueError:
            try:
                return float(expr)
            except ValueError:
                # Try to get from context
                return context.get(expr, expr)
    
    def _parse_array_items(self, items_expr: str, context: Dict[str, Any]) -> list:
        """Parse array items from expression"""
        if not items_expr:
            return []

        # Apply databinding if expression contains {variable}
        if '{' in items_expr and '}' in items_expr:
            resolved = self._apply_databinding(items_expr, context)
            # If databinding returned an array, use it
            if isinstance(resolved, list):
                return resolved
            # Otherwise continue processing the resolved value
            items_expr = str(resolved) if not isinstance(resolved, str) else resolved

        # Handle simple array notation: ["item1", "item2", "item3"]
        if items_expr.startswith('[') and items_expr.endswith(']'):
            try:
                import json
                return json.loads(items_expr)
            except json.JSONDecodeError:
                # Fallback to simple parsing
                items_str = items_expr[1:-1]  # Remove brackets
                return [item.strip().strip('"\'') for item in items_str.split(',') if item.strip()]

        # Handle variable reference from context
        if items_expr in context:
            return context[items_expr]

        # Default: treat as single item
        return [items_expr]
    
    def _parse_list_items(self, items_expr: str, delimiter: str, context: Dict[str, Any]) -> list:
        """Parse list items from delimited string"""
        if not items_expr:
            return []
        
        # Handle variable reference from context
        if items_expr in context:
            items_value = context[items_expr]
            if isinstance(items_value, list):
                return items_value
            elif isinstance(items_value, str):
                return items_value.split(delimiter)
        
        # Handle direct string list
        return items_expr.split(delimiter)
    
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
            except Exception:
                # If evaluation fails, return original placeholder
                return text

        # Mixed content (text + expressions) - need string interpolation
        def replace_variable(match):
            var_expr = match.group(1).strip()
            try:
                result = self._evaluate_databinding_expression(var_expr, context)
                return str(result)
            except Exception:
                # If evaluation fails, return original placeholder
                return match.group(0)

        # Replace all {variable} patterns using pre-compiled pattern
        result = pattern.sub(replace_variable, text)
        return result
    
    def _evaluate_databinding_expression(self, expr: str, context: Dict[str, Any]) -> Any:
        """Evaluate a databinding expression like 'variable' or 'user.name' or 'functionName(args)' or 'result[0].id'"""

        # Handle function calls first (e.g., add(5, 3))
        # Check if it looks like a function call: word followed by (
        if '(' in expr and ')' in expr and re.match(r'^\s*\w+\s*\(', expr):
            return self._evaluate_function_call(expr, context)

        # Handle array indexing (e.g., result[0] or result[0].id)
        if '[' in expr and ']' in expr:
            return self._evaluate_array_index(expr, context)

        # Handle simple variable access
        if expr in context:
            return context[expr]

        # Handle dot notation (user.name)
        if '.' in expr and '(' not in expr:
            parts = expr.split('.')
            value = context
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                elif isinstance(value, list):
                    # Handle array properties like .length
                    if part == 'length':
                        value = len(value)
                    else:
                        raise ValueError(f"Property '{part}' not found on array")
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    # For scoped variables (session.X, application.X, request.X),
                    # return '' when not found (matches get_variable default behavior)
                    if parts[0] in ('session', 'application', 'request', 'cookie', 'form', 'query'):
                        return ''
                    raise ValueError(f"Property '{part}' not found")
            return value

        # Handle arithmetic and comparison expressions (count + 1, num > 0, etc.)
        if any(op in expr for op in ['+', '-', '*', '/', '>', '<', '=', '!', '(', ')']):
            return self._evaluate_arithmetic_expression(expr, context)

        # If not found, raise error
        raise ValueError(f"Variable '{expr}' not found in context")

    def _evaluate_array_index(self, expr: str, context: Dict[str, Any]) -> Any:
        """
        Evaluate array indexing expressions like:
        - result[0]
        - result[0].id
        - users[1].name
        """
        # Use pre-compiled pattern for better performance
        match = self._array_index_pattern.match(expr.strip())

        if not match:
            raise ValueError(f"Invalid array index expression: {expr}")

        var_name = match.group(1)
        index = int(match.group(2))
        property_chain = match.group(4)  # Everything after the ]., or None

        # Get the array
        array = context.get(var_name)
        if array is None:
            raise ValueError(f"Array '{var_name}' not found in context")

        if not isinstance(array, list):
            raise ValueError(f"Variable '{var_name}' is not an array (got {type(array).__name__})")

        # Check bounds
        if index < 0 or index >= len(array):
            raise ValueError(f"Array index {index} out of bounds for '{var_name}' (length {len(array)})")

        # Get the element
        element = array[index]

        # If no property chain, return the element
        if not property_chain:
            return element

        # Navigate property chain
        value = element
        for prop in property_chain.split('.'):
            if isinstance(value, dict) and prop in value:
                value = value[prop]
            else:
                raise ValueError(f"Property '{prop}' not found in array element")

        return value

    def _evaluate_arithmetic_expression(self, expr: str, context: Dict[str, Any]) -> Any:
        """Evaluate arithmetic expressions with variables using expression cache"""
        try:
            # Try using the expression cache (compiled bytecode)
            return self._expr_cache.evaluate(expr, context)
        except (ValueError, RuntimeError):
            # Fallback to variable substitution for complex expressions
            # Sort by longest name first to avoid partial replacements (e.g., 'count' before 'c')
            sorted_vars = sorted(context.items(), key=lambda x: len(x[0]), reverse=True)
            substituted = expr
            for var_name, var_value in sorted_vars:
                if var_name in substituted:
                    if isinstance(var_value, (int, float)):
                        substituted = substituted.replace(var_name, str(var_value))
                    elif isinstance(var_value, str):
                        substituted = substituted.replace(var_name, repr(var_value))
                    elif isinstance(var_value, bool):
                        substituted = substituted.replace(var_name, str(var_value))

            try:
                # Use eval for arithmetic (safe since we control the input)
                return eval(substituted)
            except:
                raise ValueError(f"Cannot evaluate expression: {expr}")

    def _execute_set(self, set_node: SetNode, exec_context: ExecutionContext):
        """Execute q:set statement"""
        try:
            # Get dict context for evaluation
            dict_context = exec_context.get_all_variables()

            # Handle different operations
            if set_node.operation == "assign":
                value = self._execute_set_assign(set_node, dict_context)
            elif set_node.operation == "increment":
                value = self._execute_set_increment(set_node, exec_context, set_node.step)
            elif set_node.operation == "decrement":
                value = self._execute_set_decrement(set_node, exec_context, set_node.step)
            elif set_node.operation in ["add", "multiply"]:
                value = self._execute_set_arithmetic(set_node, exec_context, dict_context)
            elif set_node.operation in ["append", "prepend", "remove", "removeAt", "clear", "sort", "reverse", "unique"]:
                value = self._execute_set_array_operation(set_node, exec_context)
            elif set_node.operation in ["merge", "setProperty", "deleteProperty", "clone"]:
                value = self._execute_set_object_operation(set_node, exec_context, dict_context)
            elif set_node.operation in ["uppercase", "lowercase", "trim", "format"]:
                value = self._execute_set_transformation(set_node, exec_context)
            else:
                raise ComponentExecutionError(f"Unsupported operation: {set_node.operation}")

            # Validate the value before setting
            self._validate_set_value(set_node, value)

            # Set the variable in the appropriate scope
            # For update operations (increment, decrement, etc.) or if variable already exists,
            # update it where it is; otherwise create in specified scope
            is_update_operation = set_node.operation in ["increment", "decrement", "add", "multiply",
                                                          "append", "prepend", "remove", "removeAt",
                                                          "clear", "sort", "reverse", "unique",
                                                          "merge", "setProperty", "deleteProperty",
                                                          "uppercase", "lowercase", "trim", "format"]

            if is_update_operation or (exec_context.has_variable(set_node.name) and set_node.scope == "local"):
                # Update variable in its existing scope
                exec_context.update_variable(set_node.name, value)
            else:
                # Create new variable in specified scope
                # Inside a function, if scope is "local" (default), use "function" scope instead
                # This ensures function-level variables are accessible in nested loops
                actual_scope = set_node.scope
                if set_node.scope == "local" and exec_context.parent is not None:
                    # We're in a nested context (e.g., function) - use function scope
                    actual_scope = "function"
                exec_context.set_variable(set_node.name, value, scope=actual_scope)

            # Update self.context for backward compatibility
            self.context[set_node.name] = value

            return None  # q:set doesn't return a value

        except ValidationError as e:
            raise ComponentExecutionError(f"Validation error for '{set_node.name}': {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Set execution error for '{set_node.name}': {e}")

    def _execute_set_assign(self, set_node: SetNode, context: Dict[str, Any]) -> Any:
        """Execute assign operation"""
        # Get value (or default)
        value_expr = set_node.value if set_node.value is not None else set_node.default

        if value_expr is None:
            if not set_node.nullable:
                raise ComponentExecutionError(f"Variable '{set_node.name}' cannot be null")
            return None

        # Process databinding in value
        processed_value = self._apply_databinding(value_expr, context)

        # Convert to appropriate type
        return self._convert_to_type(processed_value, set_node.type)

    def _execute_set_increment(self, set_node: SetNode, exec_context: ExecutionContext, step: int) -> Any:
        """Execute increment operation"""
        # If value is provided, increment that; otherwise increment existing variable
        if set_node.value:
            dict_context = exec_context.get_all_variables()
            base_value = self._apply_databinding(set_node.value, dict_context)
            if not isinstance(base_value, (int, float)):
                raise ComponentExecutionError(f"Cannot increment non-numeric value: {base_value}")
            return base_value + step

        try:
            current_value = exec_context.get_variable(set_node.name)
            if not isinstance(current_value, (int, float)):
                raise ComponentExecutionError(f"Cannot increment non-numeric value: {current_value}")
            return current_value + step
        except VariableNotFoundError:
            # If variable doesn't exist, start from step
            return step

    def _execute_set_decrement(self, set_node: SetNode, exec_context: ExecutionContext, step: int) -> Any:
        """Execute decrement operation"""
        # If value is provided, decrement that; otherwise decrement existing variable
        if set_node.value:
            dict_context = exec_context.get_all_variables()
            base_value = self._apply_databinding(set_node.value, dict_context)
            if not isinstance(base_value, (int, float)):
                raise ComponentExecutionError(f"Cannot decrement non-numeric value: {base_value}")
            return base_value - step

        try:
            current_value = exec_context.get_variable(set_node.name)
            if not isinstance(current_value, (int, float)):
                raise ComponentExecutionError(f"Cannot decrement non-numeric value: {current_value}")
            return current_value - step
        except VariableNotFoundError:
            # If variable doesn't exist, start from -step
            return -step

    def _execute_set_arithmetic(self, set_node: SetNode, exec_context: ExecutionContext, context: Dict[str, Any]) -> Any:
        """Execute arithmetic operations (add, multiply)"""
        try:
            current_value = exec_context.get_variable(set_node.name)
        except VariableNotFoundError:
            current_value = 0

        if not isinstance(current_value, (int, float)):
            raise ComponentExecutionError(f"Cannot perform arithmetic on non-numeric value: {current_value}")

        # Get operand value
        operand_expr = set_node.value
        if not operand_expr:
            raise ComponentExecutionError("Arithmetic operation requires a value")

        # Get fresh context to include loop variables
        fresh_context = exec_context.get_all_variables()
        processed = self._apply_databinding(operand_expr, fresh_context)
        operand = self._convert_to_type(processed, "number")

        if set_node.operation == "add":
            return current_value + operand
        elif set_node.operation == "multiply":
            return current_value * operand

        return current_value

    def _execute_set_array_operation(self, set_node: SetNode, exec_context: ExecutionContext) -> Any:
        """Execute array operations"""
        try:
            current_value = exec_context.get_variable(set_node.name)
        except VariableNotFoundError:
            current_value = []

        if not isinstance(current_value, list):
            raise ComponentExecutionError(f"Cannot perform array operation on non-array: {type(current_value)}")

        # Create a copy to avoid modifying original
        result = current_value.copy()

        # Resolve databinding in value for append/prepend/remove operations
        resolved_value = set_node.value
        if resolved_value and set_node.operation in ("append", "prepend", "remove"):
            dict_context = exec_context.get_all_variables()
            resolved = self._apply_databinding(resolved_value, dict_context)
            if resolved is not None:
                resolved_value = resolved

        if set_node.operation == "append":
            if resolved_value:
                result.append(resolved_value)
        elif set_node.operation == "prepend":
            if resolved_value:
                result.insert(0, resolved_value)
        elif set_node.operation == "remove":
            if resolved_value and resolved_value in result:
                result.remove(resolved_value)
        elif set_node.operation == "removeAt":
            if set_node.index is not None:
                idx = int(set_node.index)
                if 0 <= idx < len(result):
                    result.pop(idx)
        elif set_node.operation == "clear":
            result = []
        elif set_node.operation == "sort":
            result.sort()
        elif set_node.operation == "reverse":
            result.reverse()
        elif set_node.operation == "unique":
            result = list(dict.fromkeys(result))  # Preserve order

        return result

    def _execute_set_object_operation(self, set_node: SetNode, exec_context: ExecutionContext, context: Dict[str, Any]) -> Any:
        """Execute object operations"""
        try:
            current_value = exec_context.get_variable(set_node.name)
        except VariableNotFoundError:
            current_value = {}

        if not isinstance(current_value, dict):
            raise ComponentExecutionError(f"Cannot perform object operation on non-object: {type(current_value)}")

        result = current_value.copy()

        if set_node.operation == "merge":
            if set_node.value:
                import json
                try:
                    merge_data = json.loads(set_node.value)
                    result.update(merge_data)
                except json.JSONDecodeError:
                    raise ComponentExecutionError(f"Invalid JSON for merge: {set_node.value}")
        elif set_node.operation == "setProperty":
            if set_node.key and set_node.value:
                result[set_node.key] = set_node.value
        elif set_node.operation == "deleteProperty":
            if set_node.key and set_node.key in result:
                del result[set_node.key]
        elif set_node.operation == "clone":
            if set_node.source:
                try:
                    source_obj = exec_context.get_variable(set_node.source)
                    if isinstance(source_obj, dict):
                        result = source_obj.copy()
                except VariableNotFoundError:
                    pass

        return result

    def _execute_set_transformation(self, set_node: SetNode, exec_context: ExecutionContext) -> Any:
        """Execute string transformation operations"""
        # If a value is provided, use that; otherwise use existing variable
        if set_node.value:
            dict_context = exec_context.get_all_variables()
            processed_value = self._apply_databinding(set_node.value, dict_context)
            value_str = str(processed_value)
        else:
            try:
                current_value = exec_context.get_variable(set_node.name)
                value_str = str(current_value)
            except VariableNotFoundError:
                value_str = ""

        if set_node.operation == "uppercase":
            return value_str.upper()
        elif set_node.operation == "lowercase":
            return value_str.lower()
        elif set_node.operation == "trim":
            return value_str.strip()
        elif set_node.operation == "format":
            # TODO: Implement format based on format attribute
            return value_str

        return value_str

    def _convert_to_type(self, value: Any, target_type: str) -> Any:
        """Convert value to target type"""
        if value is None:
            return None

        try:
            if target_type == "string":
                return str(value)
            elif target_type == "integer" or target_type == "number":
                # Try int first, then float
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return float(value)
            elif target_type == "decimal":
                return float(value)
            elif target_type == "boolean":
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ['true', '1', 'yes']
                return bool(value)
            elif target_type == "array":
                if isinstance(value, list):
                    return value
                if isinstance(value, str):
                    import json
                    return json.loads(value)
                return [value]
            elif target_type == "object":
                if isinstance(value, dict):
                    return value
                if isinstance(value, str):
                    import json
                    return json.loads(value)
                return {}
            elif target_type == "json":
                # Parse JSON string to Python object (array or dict)
                if isinstance(value, (dict, list)):
                    return value
                if isinstance(value, str):
                    import json
                    return json.loads(value)
                return value
            else:
                # Default: return as is
                return value
        except Exception as e:
            raise ComponentExecutionError(f"Type conversion error to '{target_type}': {e}")

    def _validate_set_value(self, set_node: SetNode, value: Any):
        """
        Validate a value against set_node validation rules

        Args:
            set_node: SetNode with validation rules
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        # Check required
        if set_node.required:
            is_valid, error = QuantumValidators.validate_required(value)
            if not is_valid:
                raise ValidationError(error)

        # Check nullable
        if not set_node.nullable and value is None:
            raise ValidationError(f"Variable '{set_node.name}' cannot be null")

        # If value is None and nullable=True, skip other validations
        if value is None and set_node.nullable:
            return

        # Check validate_rule (regex or built-in validator)
        if set_node.validate_rule:
            # Special case: CPF and CNPJ have digit validation
            if set_node.validate_rule == 'cpf':
                is_valid, error = QuantumValidators.validate_cpf(str(value))
            elif set_node.validate_rule == 'cnpj':
                is_valid, error = QuantumValidators.validate_cnpj(str(value))
            else:
                is_valid, error = QuantumValidators.validate(value, set_node.validate_rule)

            if not is_valid:
                raise ValidationError(error)

        # Check pattern (alias for validate_rule)
        if set_node.pattern and not set_node.validate_rule:
            is_valid, error = QuantumValidators.validate(value, set_node.pattern)
            if not is_valid:
                raise ValidationError(error)

        # Check range
        if set_node.range:
            is_valid, error = QuantumValidators.validate_range(value, set_node.range)
            if not is_valid:
                raise ValidationError(error)

        # Check enum
        if set_node.enum:
            is_valid, error = QuantumValidators.validate_enum(value, set_node.enum)
            if not is_valid:
                raise ValidationError(error)

        # Check min/max
        if set_node.min or set_node.max:
            is_valid, error = QuantumValidators.validate_min_max(
                value,
                min_val=set_node.min,
                max_val=set_node.max
            )
            if not is_valid:
                raise ValidationError(error)

        # Check minlength/maxlength
        if set_node.type == "string" and (set_node.minlength or set_node.maxlength):
            minlen = int(set_node.minlength) if set_node.minlength else None
            maxlen = int(set_node.maxlength) if set_node.maxlength else None

            is_valid, error = QuantumValidators.validate_length(
                value,
                minlength=minlen,
                maxlength=maxlen
            )
            if not is_valid:
                raise ValidationError(error)

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

        # Execute function body
        result = None
        for statement in func_node.body:
            if isinstance(statement, QuantumReturn):
                # Evaluate return value
                result = self._process_return_value(statement.value, func_context.get_all_variables())
                break
            elif isinstance(statement, SetNode):
                self._execute_set(statement, func_context)
            elif isinstance(statement, IfNode):
                result = self._execute_if(statement, func_context.get_all_variables())
                if result is not None:
                    break
            elif isinstance(statement, LoopNode):
                self._execute_loop(statement, func_context.get_all_variables(), func_context)
            elif isinstance(statement, DispatchEventNode):
                self._execute_dispatch_event(statement, func_context.get_all_variables())
            elif isinstance(statement, LogNode):
                self._execute_log(statement, func_context)
            elif isinstance(statement, DumpNode):
                self._execute_dump(statement, func_context)

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

        # Execute event handler body
        for statement in event_node.body:
            if isinstance(statement, SetNode):
                self._execute_set(statement, event_context)
            elif isinstance(statement, IfNode):
                self._execute_if(statement, event_context.get_all_variables())
            elif isinstance(statement, LoopNode):
                self._execute_loop(statement, event_context.get_all_variables())
            elif isinstance(statement, DispatchEventNode):
                self._execute_dispatch_event(statement, event_context.get_all_variables())

    def _execute_query(self, query_node: QueryNode, exec_context: ExecutionContext) -> QueryResult:
        """
        Execute database query

        Args:
            query_node: QueryNode with query configuration
            exec_context: Execution context for variables

        Returns:
            QueryResult with data and metadata

        Raises:
            ComponentExecutionError: If query execution fails
        """
        try:
            # Get dict context for parameter resolution
            dict_context = exec_context.get_all_variables()

            # Resolve and validate parameters
            resolved_params = {}
            for param_node in query_node.params:
                # Resolve parameter value (apply databinding)
                param_value = self._apply_databinding(param_node.value, dict_context)

                # Build attributes dict for validation
                attributes = {
                    'null': param_node.null,
                    'max_length': param_node.max_length,
                    'scale': param_node.scale
                }

                # Validate and convert parameter
                try:
                    validated_value = QueryValidator.validate_param(
                        param_value,
                        param_node.param_type,
                        attributes
                    )
                    resolved_params[param_node.name] = validated_value
                except QueryValidationError as e:
                    raise ComponentExecutionError(
                        f"Parameter '{param_node.name}' validation failed: {e}"
                    )

            # Sanitize SQL (basic check)
            QueryValidator.sanitize_sql(query_node.sql)

            # Check if this is a knowledge base query (virtual datasource)
            if query_node.datasource and query_node.datasource.startswith('knowledge:'):
                return self._execute_knowledge_query(query_node, resolved_params, exec_context)

            # Check if this is a Query of Queries (in-memory SQL)
            if query_node.source:
                return self._execute_query_of_queries(query_node, dict_context, resolved_params, exec_context)

            # Handle pagination if enabled
            pagination_metadata = None
            sql_to_execute = query_node.sql

            if query_node.paginate:
                # Execute COUNT(*) query to get total records
                count_sql = self._generate_count_query(query_node.sql)
                count_result = self.database_service.execute_query(
                    query_node.datasource,
                    count_sql,
                    resolved_params
                )

                # Get total count from result
                total_records = count_result.data[0]['count'] if count_result.data else 0

                # Calculate pagination metadata
                page = query_node.page if query_node.page is not None else 1
                page_size = query_node.page_size
                total_pages = (total_records + page_size - 1) // page_size  # Ceiling division

                # Add LIMIT and OFFSET to SQL
                offset = (page - 1) * page_size
                sql_to_execute = f"{query_node.sql}\nLIMIT {page_size} OFFSET {offset}"

                # Store pagination metadata
                pagination_metadata = {
                    'totalRecords': total_records,
                    'totalPages': total_pages,
                    'currentPage': page,
                    'pageSize': page_size,
                    'hasNextPage': page < total_pages,
                    'hasPreviousPage': page > 1,
                    'startRecord': offset + 1 if total_records > 0 else 0,
                    'endRecord': min(offset + page_size, total_records)
                }

            # Execute query via DatabaseService
            result = self.database_service.execute_query(
                query_node.datasource,
                sql_to_execute,
                resolved_params
            )

            # Store result in context with query name
            # Store both as QueryResult object and as plain dict for template access
            result_dict = result.to_dict()

            # Add pagination metadata if enabled
            if pagination_metadata:
                result_dict['pagination'] = pagination_metadata

            # Make data accessible directly as array (for q:loop)
            exec_context.set_variable(query_node.name, result.data, scope="component")

            # Also store full result object with metadata
            exec_context.set_variable(f"{query_node.name}_result", result_dict, scope="component")

            # Store in self.context for backward compatibility
            self.context[query_node.name] = result.data
            self.context[f"{query_node.name}_result"] = result_dict

            # For single-row results (INSERT RETURNING, etc.), expose fields directly
            # Allows {insertResult.id} instead of {insertResult[0].id}
            if result.data and len(result.data) == 1 and isinstance(result.data[0], dict):
                for field_name, field_value in result.data[0].items():
                    dotted_key = f"{query_node.name}.{field_name}"
                    exec_context.set_variable(dotted_key, field_value, scope="component")
                    self.context[dotted_key] = field_value

            # If result variable name specified, store metadata separately
            if query_node.result:
                exec_context.set_variable(query_node.result, result_dict, scope="component")
                self.context[query_node.result] = result_dict

            return result

        except QueryValidationError as e:
            raise ComponentExecutionError(f"Query validation error in '{query_node.name}': {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Query execution error in '{query_node.name}': {e}")

    def _generate_count_query(self, original_sql: str) -> str:
        """
        Generate a COUNT(*) query from the original SQL.
        Wraps the original query in a subquery to handle complex cases.

        Example:
            Input:  SELECT id, name FROM users WHERE status = 'active' ORDER BY created_at DESC
            Output: SELECT COUNT(*) as count FROM (SELECT id, name FROM users WHERE status = 'active') AS count_query

        This approach works for:
        - Simple queries
        - Queries with JOINs
        - Queries with GROUP BY
        - Queries with complex WHERE clauses
        """
        # Normalize SQL (remove extra whitespace, newlines)
        sql = ' '.join(original_sql.split())

        # Remove ORDER BY, LIMIT, OFFSET clauses using pre-compiled patterns
        sql = self._order_by_pattern.sub('', sql)
        sql = self._limit_pattern.sub('', sql)
        sql = self._offset_pattern.sub('', sql)

        # Wrap in COUNT subquery
        # This handles all edge cases: JOINs, GROUP BY, complex WHERE, etc.
        count_sql = f"SELECT COUNT(*) as count FROM ({sql}) AS count_query"

        return count_sql

    def _execute_query_of_queries(self, query_node: 'QueryNode', context: Dict[str, Any],
                                   params: Dict[str, Any], exec_context: 'ExecutionContext') -> 'QueryResult':
        """
        Execute Query of Queries - SQL on in-memory result sets.

        Uses SQLite in-memory database to execute SQL on previous query results.

        Args:
            query_node: QueryNode with source attribute set
            context: Variable context
            params: Resolved query parameters
            exec_context: Execution context

        Returns:
            QueryResult with data and metadata

        Raises:
            ComponentExecutionError: If source query not found or execution fails
        """
        import sqlite3
        import time
        from .database_service import QueryResult

        try:
            # Get source query result from context
            source_name = query_node.source
            source_data = context.get(source_name) or exec_context.get_variable(source_name)

            if source_data is None:
                raise ComponentExecutionError(
                    f"Source query '{source_name}' not found for Query of Queries"
                )

            if not isinstance(source_data, list):
                raise ComponentExecutionError(
                    f"Source '{source_name}' is not a query result (got {type(source_data).__name__})"
                )

            if not source_data:
                # Empty source - return empty result
                return QueryResult(
                    success=True,
                    data=[],
                    record_count=0,
                    column_list=[],
                    execution_time=0,
                    sql=query_node.sql
                )

            # Create in-memory SQLite database
            conn = sqlite3.connect(':memory:')
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()

            # Infer table structure from first row
            first_row = source_data[0]
            if not isinstance(first_row, dict):
                raise ComponentExecutionError(
                    f"Source data must be list of dictionaries (got {type(first_row).__name__})"
                )

            # Create table schema
            columns = list(first_row.keys())
            column_defs = ', '.join([f'"{col}" TEXT' for col in columns])  # Use TEXT for simplicity
            create_table_sql = f'CREATE TABLE source_table ({column_defs})'
            cursor.execute(create_table_sql)

            # Insert source data
            placeholders = ', '.join(['?' for _ in columns])
            insert_sql = f'INSERT INTO source_table VALUES ({placeholders})'
            for row in source_data:
                values = [row.get(col) for col in columns]
                cursor.execute(insert_sql, values)

            # Replace source name in SQL with actual table name
            # Support both "FROM source" and "FROM {source}" syntax
            sql = query_node.sql
            sql = sql.replace(f'FROM {source_name}', 'FROM source_table')
            sql = sql.replace(f'FROM {{{source_name}}}', 'FROM source_table')

            # Apply parameter binding (convert :name to ?)
            for param_name, param_value in params.items():
                sql = sql.replace(f':{param_name}', '?')

            # Execute query
            start_time = time.time()
            cursor.execute(sql, list(params.values()) if params else [])
            result_rows = cursor.fetchall()
            execution_time = (time.time() - start_time) * 1000  # Convert to ms

            # Convert to list of dicts
            result_data = []
            if result_rows:
                column_names = [description[0] for description in cursor.description]
                for row in result_rows:
                    result_data.append(dict(zip(column_names, row)))

            # Close connection
            conn.close()

            # Return QueryResult
            result = QueryResult(
                success=True,
                data=result_data,
                record_count=len(result_data),
                column_list=column_names if result_data else [],
                execution_time=int(execution_time),
                sql=query_node.sql
            )

            # Store result in context (same as regular query)
            result_dict = result.to_dict()
            exec_context.set_variable(query_node.name, result.data, scope="component")
            exec_context.set_variable(f"{query_node.name}_result", result_dict, scope="component")
            self.context[query_node.name] = result.data
            self.context[f"{query_node.name}_result"] = result_dict

            # Single-row field exposure
            if result.data and len(result.data) == 1 and isinstance(result.data[0], dict):
                for field_name, field_value in result.data[0].items():
                    dotted_key = f"{query_node.name}.{field_name}"
                    exec_context.set_variable(dotted_key, field_value, scope="component")
                    self.context[dotted_key] = field_value

            return result

        except sqlite3.Error as e:
            raise ComponentExecutionError(f"Query of Queries SQL error in '{query_node.name}': {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Query of Queries execution error in '{query_node.name}': {e}")

    def _execute_invoke(self, invoke_node: InvokeNode, exec_context: ExecutionContext):
        """
        Execute invocation (function, component, HTTP, etc.)

        Args:
            invoke_node: InvokeNode with invocation configuration
            exec_context: Execution context for variables

        Returns:
            None (stores result in context)

        Raises:
            ComponentExecutionError: If invocation fails
        """
        try:
            # Get dict context for parameter resolution and databinding
            dict_context = exec_context.get_all_variables()

            # Get invocation type
            invocation_type = invoke_node.get_invocation_type()

            if invocation_type == "unknown":
                raise ComponentExecutionError(
                    f"Invoke '{invoke_node.name}' requires one of: function, component, url, endpoint, or service"
                )

            # Build invocation parameters based on type
            if invocation_type == "function":
                params = self._build_function_invoke_params(invoke_node, dict_context)
            elif invocation_type == "component":
                params = self._build_component_invoke_params(invoke_node, dict_context)
            elif invocation_type == "http":
                params = self._build_http_invoke_params(invoke_node, dict_context)
            else:
                raise ComponentExecutionError(f"Unsupported invocation type: {invocation_type}")

            # Check cache if enabled
            if invoke_node.cache:
                cache_key = f"invoke_{invoke_node.name}_{hash(str(params))}"
                cached_result = self.invocation_service.get_from_cache(cache_key)
                if cached_result is not None:
                    self._store_invoke_result(invoke_node, cached_result, exec_context)
                    return

            # Execute invocation
            result = self.invocation_service.invoke(
                invocation_type,
                params,
                context=self  # Pass runtime as context for function/component calls
            )

            # Cache result if enabled
            if invoke_node.cache and result.success:
                cache_key = f"invoke_{invoke_node.name}_{hash(str(params))}"
                self.invocation_service.put_in_cache(cache_key, result, invoke_node.ttl)

            # Store result in context
            self._store_invoke_result(invoke_node, result, exec_context)

        except Exception as e:
            raise ComponentExecutionError(f"Invoke execution error in '{invoke_node.name}': {e}")

    def _build_function_invoke_params(self, invoke_node: InvokeNode, dict_context: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for function invocation"""
        args = {}

        # Resolve parameters
        for param in invoke_node.params:
            param_value = self._apply_databinding(param.default if param.default else "", dict_context)
            args[param.name] = param_value

        return {
            'function': invoke_node.function,
            'args': args
        }

    def _build_component_invoke_params(self, invoke_node: InvokeNode, dict_context: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for component invocation"""
        args = {}

        # Resolve parameters
        for param in invoke_node.params:
            param_value = self._apply_databinding(param.default if param.default else "", dict_context)
            args[param.name] = param_value

        return {
            'component': invoke_node.component,
            'args': args
        }

    def _build_http_invoke_params(self, invoke_node: InvokeNode, dict_context: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for HTTP invocation"""
        # Resolve URL (may contain databinding)
        url = self._apply_databinding(invoke_node.url, dict_context)

        # Build headers
        headers = {}
        for header_node in invoke_node.headers:
            header_value = self._apply_databinding(header_node.value, dict_context)
            headers[header_node.name] = header_value

        # Add content-type header if not present
        if 'Content-Type' not in headers and 'content-type' not in headers:
            headers['Content-Type'] = invoke_node.content_type

        # Build query parameters
        query_params = {}
        for param in invoke_node.params:
            param_value = self._apply_databinding(param.default if param.default else "", dict_context)
            query_params[param.name] = param_value

        # Resolve body (may contain databinding)
        body = None
        if invoke_node.body:
            body = self._apply_databinding(invoke_node.body, dict_context)
            # Try to parse as JSON if it's a string and content-type is JSON
            if isinstance(body, str) and 'json' in invoke_node.content_type.lower():
                try:
                    import json
                    body = json.loads(body)
                except:
                    pass  # Keep as string if not valid JSON

        return {
            'url': url,
            'method': invoke_node.method,
            'headers': headers,
            'params': query_params,
            'body': body,
            'auth_type': invoke_node.auth_type,
            'auth_token': self._apply_databinding(invoke_node.auth_token, dict_context) if invoke_node.auth_token else None,
            'auth_header': invoke_node.auth_header,
            'auth_username': self._apply_databinding(invoke_node.auth_username, dict_context) if invoke_node.auth_username else None,
            'auth_password': self._apply_databinding(invoke_node.auth_password, dict_context) if invoke_node.auth_password else None,
            'timeout': invoke_node.timeout,
            'retry': invoke_node.retry,
            'retry_delay': invoke_node.retry_delay,
            'response_format': invoke_node.response_format
        }

    def _store_invoke_result(self, invoke_node: InvokeNode, result, exec_context: ExecutionContext):
        """Store invocation result in context"""
        # Store data directly (for easy access in templates)
        exec_context.set_variable(invoke_node.name, result.data, scope="component")
        self.context[invoke_node.name] = result.data

        # Build result object
        result_dict = {
            'success': result.success,
            'data': result.data,
            'error': result.error,
            'executionTime': result.execution_time,
            'invocationType': result.invocation_type,
            'metadata': result.metadata
        }

        # Store full result object
        exec_context.set_variable(f"{invoke_node.name}_result", result_dict, scope="component")
        self.context[f"{invoke_node.name}_result"] = result_dict

        # If result variable name specified, store metadata separately
        if invoke_node.result:
            exec_context.set_variable(invoke_node.result, result_dict, scope="component")
            self.context[invoke_node.result] = result_dict

    def _execute_data(self, data_node: DataNode, exec_context: ExecutionContext):
        """
        Execute data import and transformation

        Args:
            data_node: DataNode with import configuration
            exec_context: Execution context for variables

        Returns:
            None (stores result in context)

        Raises:
            ComponentExecutionError: If data import fails
        """
        try:
            # Get dict context for parameter resolution and databinding
            dict_context = exec_context.get_all_variables()

            # Resolve source (may contain databinding)
            source = self._apply_databinding(data_node.source, dict_context)

            # Build parameters for data import
            params = {
                'cache': data_node.cache,
                'ttl': data_node.ttl,
                'delimiter': data_node.delimiter,
                'quote': data_node.quote,
                'header': data_node.header,
                'encoding': data_node.encoding,
                'skip_rows': data_node.skip_rows,
                'xpath': data_node.xpath,
                'namespace': data_node.namespace,
                'columns': [],
                'fields': [],
                'transforms': [],
                'headers': []
            }

            # Add column definitions (for CSV)
            for col in data_node.columns:
                params['columns'].append({
                    'name': col.name,
                    'type': col.col_type,
                    'required': col.required,
                    'default': col.default
                })

            # Add field definitions (for XML)
            for field in data_node.fields:
                params['fields'].append({
                    'name': field.name,
                    'xpath': field.xpath,
                    'type': field.field_type
                })

            # Add HTTP headers
            for header in data_node.headers:
                resolved_value = self._apply_databinding(header.value, dict_context)
                params['headers'].append({
                    'name': header.name,
                    'value': resolved_value
                })

            # Add transformations
            for transform in data_node.transforms:
                for operation in transform.operations:
                    op_dict = {
                        'type': operation.__class__.__name__.replace('Node', '').lower()
                    }

                    if hasattr(operation, 'condition'):
                        # Filter operation
                        op_dict['condition'] = operation.condition
                    elif hasattr(operation, 'by'):
                        # Sort operation
                        op_dict['by'] = operation.by
                        op_dict['order'] = operation.order
                    elif hasattr(operation, 'value'):
                        # Limit operation
                        op_dict['value'] = operation.value
                    elif hasattr(operation, 'field'):
                        # Compute operation
                        op_dict['field'] = operation.field
                        op_dict['expression'] = operation.expression
                        op_dict['type'] = operation.comp_type

                    params['transforms'].append(op_dict)

            # Execute data import
            result = self.data_import_service.import_data(
                data_node.data_type,
                source,
                params,
                context=exec_context
            )

            # Store result in context
            self._store_data_result(data_node, result, exec_context)

        except Exception as e:
            raise ComponentExecutionError(f"Data import error in '{data_node.name}': {e}")

    def _store_data_result(self, data_node: DataNode, result, exec_context: ExecutionContext):
        """Store data import result in context"""
        # Store data directly (for easy access in templates and loops)
        exec_context.set_variable(data_node.name, result.data, scope="component")
        self.context[data_node.name] = result.data

        # Build result object
        result_dict = {
            'success': result.success,
            'data': result.data,
            'error': result.error,
            'recordCount': result.recordCount,
            'loadTime': result.loadTime,
            'cached': result.cached,
            'source': result.source
        }

        # Store full result object
        exec_context.set_variable(f"{data_node.name}_result", result_dict, scope="component")
        self.context[f"{data_node.name}_result"] = result_dict

        # If result variable name specified, store metadata separately
        if data_node.result:
            exec_context.set_variable(data_node.result, result_dict, scope="component")
            self.context[data_node.result] = result_dict

    def get_function(self, function_name: str) -> FunctionNode:
        """Get function by name from current component"""
        if not self.current_component:
            return None

        for func in self.current_component.functions:
            if func.name == function_name:
                return func

        return None


    def _execute_log(self, log_node: LogNode, exec_context: ExecutionContext):
        """
        Execute logging statement

        Args:
            log_node: LogNode with logging configuration
            exec_context: Execution context for variables

        Returns:
            None (logs to configured output)

        Raises:
            ComponentExecutionError: If logging fails
        """
        try:
            # Get dict context for databinding
            dict_context = exec_context.get_all_variables()

            # Check conditional execution
            if log_node.when:
                condition_result = self._apply_databinding(log_node.when, dict_context)
                if not self.logging_service.should_log(condition_result):
                    return

            # Resolve message (apply databinding)
            message = self._apply_databinding(log_node.message, dict_context)

            # Resolve context data if provided
            context_data = None
            if log_node.context:
                # Parse context as JSON or variable reference
                context_expr = self._apply_databinding(log_node.context, dict_context)
                if isinstance(context_expr, dict):
                    context_data = context_expr
                elif isinstance(context_expr, str):
                    try:
                        import json
                        context_data = json.loads(context_expr)
                    except:
                        # Not JSON - treat as single value
                        context_data = {'value': context_expr}

            # Resolve correlation_id if provided
            correlation_id = None
            if log_node.correlation_id:
                correlation_id = self._apply_databinding(log_node.correlation_id, dict_context)

            # Execute logging
            result = self.logging_service.log(
                level=log_node.level,
                message=str(message),
                context=context_data,
                correlation_id=correlation_id
            )

            # Note: We don't store log result in context since logging is side-effect only
            # However, we could expose {log_result.success} if needed in future

        except Exception as e:
            raise ComponentExecutionError(f"Logging error: {e}")

    def _execute_dump(self, dump_node: DumpNode, exec_context: ExecutionContext):
        """
        Execute variable dump/inspection

        Args:
            dump_node: DumpNode with dump configuration
            exec_context: Execution context for variables

        Returns:
            str: Formatted dump output (stored in context and printed)

        Raises:
            ComponentExecutionError: If dump fails
        """
        try:
            # Get dict context for databinding
            dict_context = exec_context.get_all_variables()

            # Check conditional execution
            if dump_node.when:
                condition_result = self._apply_databinding(dump_node.when, dict_context)
                if not self.dump_service.should_dump(condition_result):
                    return

            # Resolve variable to dump
            var_expr = dump_node.var
            try:
                var_value = self._apply_databinding(var_expr, dict_context)
            except Exception as e:
                # If variable not found, dump the error
                var_value = f"<Variable '{var_expr}' not found: {e}>"

            # Generate dump output
            dump_output = self.dump_service.dump(
                var=var_value,
                label=dump_node.label,
                format=dump_node.format,
                depth=dump_node.depth
            )

            # Print dump output (for development/debugging)
            print(dump_output)

            # Also store in context for potential template rendering
            dump_var_name = f"_dump_{dump_node.label.replace(' ', '_')}"
            exec_context.set_variable(dump_var_name, dump_output, scope="component")
            self.context[dump_var_name] = dump_output

            return dump_output

        except Exception as e:
            raise ComponentExecutionError(f"Dump error: {e}")

    def execute_function(self, function_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute function and return result"""
        try:
            result = self.function_registry.call_function(function_name, args, self)
            return {
                'success': True,
                'data': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': {
                    'message': str(e),
                    'type': type(e).__name__
                }
            }

    def _execute_file(self, file_node: FileNode, exec_context: ExecutionContext):
        """
        Execute file operation (upload, delete, etc.)
        
        Phase H: File Uploads
        
        Args:
            file_node: FileNode with file operation configuration
            exec_context: Execution context for variables
            
        Returns:
            None (stores result in context if result variable specified)
            
        Raises:
            ComponentExecutionError: If file operation fails
        """
        try:
            # Get dict context for databinding
            dict_context = exec_context.get_all_variables()
            
            if file_node.action == 'upload':
                # Resolve file variable (contains FileStorage from Flask)
                file_var = file_node.file.strip('{}')  # Remove curly braces if present
                file_obj = dict_context.get(file_var)
                
                if not file_obj:
                    raise ComponentExecutionError(f"File variable '{file_var}' not found in context")
                
                # Resolve destination (apply databinding)
                destination = self._apply_databinding(file_node.destination, dict_context)
                
                # Upload file using FileUploadService
                result = self.file_upload_service.upload_file(
                    file=file_obj,
                    destination=destination,
                    name_conflict=file_node.name_conflict
                )
                
                # Store result in context if result variable specified
                if file_node.result:
                    exec_context.set_variable(file_node.result, result, scope="component")
                    self.context[file_node.result] = result
                
                # Also store upload info in default variable based on original file var
                exec_context.set_variable(f"{file_var}_upload", result, scope="component")
                self.context[f"{file_var}_upload"] = result
                
                return result
                
            elif file_node.action == 'delete':
                # Resolve filepath
                filepath = self._apply_databinding(file_node.file, dict_context)
                
                # Delete file
                result = self.file_upload_service.delete_file(filepath)
                
                # Store result if variable specified
                if file_node.result:
                    exec_context.set_variable(file_node.result, result, scope="component")
                    self.context[file_node.result] = result
                
                return result
            
            else:
                raise ComponentExecutionError(f"Unsupported file action: {file_node.action}")
                
        except FileUploadError as e:
            raise ComponentExecutionError(f"File operation error: {e}")
        except Exception as e:
            raise ComponentExecutionError(f"File execution error: {e}")

    def _execute_mail(self, mail_node: MailNode, exec_context: ExecutionContext):
        """
        Execute email sending (q:mail).
        
        Phase I: Email Sending
        
        Args:
            mail_node: MailNode with email configuration
            exec_context: Execution context for variables
            
        Returns:
            Email send result dict
            
        Raises:
            ComponentExecutionError: If email sending fails
        """
        try:
            # Get dict context for databinding
            dict_context = exec_context.get_all_variables()
            
            # Resolve all email properties with databinding
            to = self._apply_databinding(mail_node.to, dict_context)
            subject = self._apply_databinding(mail_node.subject, dict_context)
            body = self._apply_databinding(mail_node.body, dict_context)
            
            from_addr = None
            if mail_node.from_addr:
                from_addr = self._apply_databinding(mail_node.from_addr, dict_context)
            
            cc = None
            if mail_node.cc:
                cc = self._apply_databinding(mail_node.cc, dict_context)
            
            bcc = None
            if mail_node.bcc:
                bcc = self._apply_databinding(mail_node.bcc, dict_context)
            
            reply_to = None
            if mail_node.reply_to:
                reply_to = self._apply_databinding(mail_node.reply_to, dict_context)
            
            # Send email using EmailService
            result = self.email_service.send_email(
                to=to,
                subject=subject,
                body=body,
                from_addr=from_addr,
                cc=cc,
                bcc=bcc,
                reply_to=reply_to,
                email_type=mail_node.type,
                attachments=mail_node.attachments
            )
            
            # Store result in context
            exec_context.set_variable('_mail_result', result, scope="component")
            self.context['_mail_result'] = result
            
            return result
            
        except EmailError as e:
            raise ComponentExecutionError(f"Email sending error: {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Mail execution error: {e}")

    def _execute_transaction(self, transaction_node: TransactionNode, exec_context: ExecutionContext):
        """
        Execute database transaction (q:transaction).

        Phase D: Database Backend

        Ensures atomic execution of database operations. All statements
        within the transaction succeed together or fail together.

        Args:
            transaction_node: TransactionNode with statements to execute
            exec_context: Execution context for variables

        Returns:
            Transaction result dict with success status

        Raises:
            ComponentExecutionError: If transaction fails
        """
        try:
            # Get dict context for databinding
            dict_context = exec_context.get_all_variables()

            # Determine datasource (use first query's datasource or default)
            datasource_name = "default"
            for stmt in transaction_node.statements:
                if isinstance(stmt, QueryNode) and stmt.datasource:
                    datasource_name = stmt.datasource
                    break

            # Begin transaction
            transaction_context = self.database_service.begin_transaction(datasource_name)

            results = []
            try:
                # Execute all statements in transaction
                for statement in transaction_node.statements:
                    # Execute statement (queries, sets, etc.)
                    result = self._execute_statement(statement, exec_context)
                    results.append(result)

                # All succeeded - commit transaction
                success = self.database_service.commit_transaction(transaction_context)

                transaction_result = {
                    'success': success,
                    'committed': True,
                    'isolation_level': transaction_node.isolation_level,
                    'statement_count': len(transaction_node.statements),
                    'results': results
                }

            except Exception as stmt_error:
                # Any statement failed - rollback transaction
                self.database_service.rollback_transaction(transaction_context)

                transaction_result = {
                    'success': False,
                    'rolled_back': True,
                    'error': str(stmt_error),
                    'isolation_level': transaction_node.isolation_level
                }

                # Re-raise the error
                raise ComponentExecutionError(f"Transaction failed and was rolled back: {stmt_error}")

            # Store result in context
            exec_context.set_variable('_transaction_result', transaction_result, scope="component")
            self.context['_transaction_result'] = transaction_result

            return transaction_result

        except ComponentExecutionError:
            # Re-raise component errors
            raise
        except Exception as e:
            raise ComponentExecutionError(f"Transaction execution error: {e}")

    def _execute_llm(self, llm_node: LLMNode, exec_context: ExecutionContext):
        """
        Execute LLM invocation (q:llm) via Ollama-compatible API.

        Supports two modes:
        - Completion: single prompt via /api/generate
        - Chat: message list via /api/chat

        Args:
            llm_node: LLMNode with LLM configuration
            exec_context: Execution context for variables

        Returns:
            LLM result dict

        Raises:
            ComponentExecutionError: If LLM invocation fails
        """
        try:
            dict_context = exec_context.get_all_variables()

            # Use node-level endpoint override or service default
            service = self.llm_service
            if llm_node.endpoint:
                endpoint = self._apply_databinding(llm_node.endpoint, dict_context)
                service = LLMService(base_url=endpoint)

            model = llm_node.model
            if model:
                model = self._apply_databinding(str(model), dict_context)

            # Decide: chat mode (messages) vs completion mode (prompt)
            if llm_node.messages:
                # Chat mode
                messages = []
                for msg in llm_node.messages:
                    content = self._apply_databinding(msg.content, dict_context)
                    messages.append({"role": msg.role, "content": str(content)})

                result = service.chat(
                    messages=messages,
                    model=model,
                    temperature=llm_node.temperature,
                    max_tokens=llm_node.max_tokens,
                    response_format=llm_node.response_format,
                    timeout=llm_node.timeout,
                )
            else:
                # Completion mode
                prompt = ""
                if llm_node.prompt:
                    prompt = str(self._apply_databinding(llm_node.prompt, dict_context))

                system = None
                if llm_node.system:
                    system = str(self._apply_databinding(llm_node.system, dict_context))

                result = service.generate(
                    prompt=prompt,
                    model=model,
                    system=system,
                    temperature=llm_node.temperature,
                    max_tokens=llm_node.max_tokens,
                    response_format=llm_node.response_format,
                    timeout=llm_node.timeout,
                )

            # Store response text as {name}
            response_text = result.get("data", "")
            exec_context.set_variable(llm_node.name, response_text, scope="component")
            self.context[llm_node.name] = response_text

            # Store full result object as {name_result}
            result_key = f"{llm_node.name}_result"
            exec_context.set_variable(result_key, result, scope="component")
            self.context[result_key] = result

            return result

        except LLMError as e:
            raise ComponentExecutionError(f"LLM error: {e}")
        except Exception as e:
            raise ComponentExecutionError(f"LLM execution error: {e}")

    # ============================================
    # AGENT EXECUTION (q:agent with tool use)
    # ============================================

    def _execute_agent(self, agent_node: AgentNode, exec_context: ExecutionContext):
        """
        Execute q:agent - AI agent with tool use capabilities.

        Uses the ReAct pattern:
        1. THINK: LLM analyzes task and available tools
        2. ACT: Execute a tool
        3. OBSERVE: Process tool result
        4. REPEAT: Until task complete or max_iterations

        Args:
            agent_node: AgentNode with tools and task
            exec_context: Current execution context

        Returns:
            AgentResult dict with success, result, actions, etc.
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Get agent service
            agent_service = get_agent_service()

            # Get context as dict for databinding
            dict_context = exec_context.to_dict()

            # Resolve instruction with databinding
            instruction = ""
            if agent_node.instruction:
                instruction = str(self._apply_databinding(
                    agent_node.instruction.content, dict_context
                ))

            # Resolve task and context with databinding
            task = ""
            context = ""
            if agent_node.execute:
                task = str(self._apply_databinding(
                    agent_node.execute.task, dict_context
                ))
                if agent_node.execute.context:
                    context = str(self._apply_databinding(
                        agent_node.execute.context, dict_context
                    ))

            # Build tool definitions
            tools = []
            for tool_node in agent_node.tools:
                tool_def = {
                    "name": tool_node.name,
                    "description": tool_node.description,
                    "params": [
                        {
                            "name": p.name,
                            "type": p.type,
                            "required": p.required,
                            "default": p.default,
                            "description": p.description
                        }
                        for p in tool_node.params
                    ],
                    "body": tool_node.body  # AST nodes for execution
                }
                tools.append(tool_def)

            # Create tool executor function
            def tool_executor(tool_name: str, tool_args: dict, body: list):
                """Execute tool body with arguments in context."""
                # Set tool arguments in context
                for arg_name, arg_value in tool_args.items():
                    exec_context.set_variable(arg_name, arg_value, scope="local")
                    self.context[arg_name] = arg_value

                # Execute body statements
                result = None
                for node in body:
                    result = self._execute_node(node, exec_context)

                # Check for return value
                return_val = exec_context.get_variable("_return", None)
                if return_val is not None:
                    return return_val
                return result

            # Execute agent
            logger.info(f"Executing agent '{agent_node.name}' with task: {task[:100]}...")

            # Resolve API key with databinding (for env vars)
            api_key = ""
            if agent_node.api_key:
                api_key = str(self._apply_databinding(
                    agent_node.api_key, dict_context
                ))

            result = agent_service.execute(
                instruction=instruction,
                tools=tools,
                task=task,
                context=context,
                model=agent_node.model,
                endpoint=agent_node.endpoint,
                provider=agent_node.provider,
                api_key=api_key,
                max_iterations=agent_node.max_iterations,
                timeout_ms=agent_node.timeout,
                tool_executor=tool_executor
            )

            # Store response as {name}
            exec_context.set_variable(agent_node.name, result.result, scope="component")
            self.context[agent_node.name] = result.result

            # Store full result as {name}_result
            result_key = f"{agent_node.name}_result"
            result_dict = result.to_dict()
            exec_context.set_variable(result_key, result_dict, scope="component")
            self.context[result_key] = result_dict

            logger.info(f"Agent '{agent_node.name}' completed: success={result.success}, "
                       f"actions={result.action_count}, time={result.execution_time_ms:.0f}ms")

            return result_dict

        except AgentError as e:
            raise ComponentExecutionError(f"Agent error: {e}")
        except Exception as e:
            logger.exception(f"Agent execution error: {e}")
            raise ComponentExecutionError(f"Agent execution error: {e}")

    # ============================================
    # MULTI-AGENT TEAM EXECUTION (q:team)
    # ============================================

    def _execute_team(self, team_node: AgentTeamNode, exec_context: ExecutionContext):
        """
        Execute q:team - multi-agent collaboration.

        Coordinates multiple agents that can hand off tasks to each other,
        share context, and work together to complete complex tasks.

        Args:
            team_node: AgentTeamNode with agents, shared state, and task
            exec_context: Current execution context

        Returns:
            TeamResult dict with success, final response, handoffs, etc.
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Get multi-agent service
            multi_agent_service = get_multi_agent_service()

            # Get context as dict for databinding
            dict_context = exec_context.to_dict()

            # Initialize shared context from q:shared
            shared = {}
            for stmt in team_node.shared:
                self._execute_statement(stmt, exec_context)
                if hasattr(stmt, 'name'):
                    value = exec_context.get_variable(stmt.name)
                    shared[stmt.name] = value

            # Build agent configurations
            agents = {}
            for agent_node in team_node.agents:
                # Resolve instruction with databinding
                instruction = ""
                if agent_node.instruction:
                    instruction = str(self._apply_databinding(
                        agent_node.instruction.content, dict_context
                    ))

                # Resolve API key with databinding
                api_key = ""
                if agent_node.api_key:
                    api_key = str(self._apply_databinding(
                        agent_node.api_key, dict_context
                    ))

                # Build tool definitions
                tools = []
                for tool_node in agent_node.tools:
                    if tool_node.builtin:
                        # Built-in tool - just need name and builtin flag
                        tool_def = {
                            "name": tool_node.name,
                            "builtin": True
                        }
                    else:
                        # Custom tool with body
                        tool_def = {
                            "name": tool_node.name,
                            "description": tool_node.description,
                            "params": [
                                {
                                    "name": p.name,
                                    "type": p.type,
                                    "required": p.required,
                                    "default": p.default,
                                    "description": p.description
                                }
                                for p in tool_node.params
                            ],
                            "body": tool_node.body
                        }
                    tools.append(tool_def)

                agents[agent_node.name] = {
                    "instruction": instruction,
                    "model": agent_node.model,
                    "endpoint": agent_node.endpoint,
                    "provider": agent_node.provider,
                    "api_key": api_key,
                    "max_iterations": agent_node.max_iterations,
                    "timeout": agent_node.timeout,
                    "tools": tools
                }

            # Create team
            team = multi_agent_service.create_team(
                name=team_node.name,
                agents=agents,
                shared=shared,
                supervisor=team_node.supervisor,
                max_handoffs=team_node.max_handoffs,
                max_total_iterations=team_node.max_total_iterations
            )

            # Create tool executor function for custom tools
            def tool_executor(tool_name: str, tool_args: dict, body: list):
                """Execute tool body with arguments in context."""
                # Set tool arguments in context
                for arg_name, arg_value in tool_args.items():
                    exec_context.set_variable(arg_name, arg_value, scope="local")
                    self.context[arg_name] = arg_value

                # Execute body statements
                result = None
                for node in body:
                    result = self._execute_node(node, exec_context)

                # Check for return value
                return_val = exec_context.get_variable("_return", None)
                if return_val is not None:
                    return return_val
                return result

            # Resolve task and context with databinding
            task = ""
            context = ""
            entry_agent = None
            if team_node.execute:
                task = str(self._apply_databinding(
                    team_node.execute.task, dict_context
                ))
                if team_node.execute.context:
                    context = str(self._apply_databinding(
                        team_node.execute.context, dict_context
                    ))
                if team_node.execute.entry:
                    entry_agent = team_node.execute.entry

            logger.info(f"Executing team '{team_node.name}' with entry agent '{entry_agent or team_node.supervisor}'")

            # Execute team
            result = team.execute(
                task=task,
                entry_agent=entry_agent,
                context=context,
                tool_executor=tool_executor
            )

            # Store final response as {name}
            exec_context.set_variable(team_node.name, result.final_response, scope="component")
            self.context[team_node.name] = result.final_response

            # Store full result as {name}_result
            result_key = f"{team_node.name}_result"
            result_dict = result.to_dict()
            exec_context.set_variable(result_key, result_dict, scope="component")
            self.context[result_key] = result_dict

            logger.info(f"Team '{team_node.name}' completed: success={result.success}, "
                       f"handoffs={len(result.handoffs)}, final_agent={result.final_agent}, "
                       f"time={result.execution_time_ms:.0f}ms")

            return result_dict

        except AgentError as e:
            raise ComponentExecutionError(f"Team agent error: {e}")
        except Exception as e:
            logger.exception(f"Team execution error: {e}")
            raise ComponentExecutionError(f"Team execution error: {e}")

    # ============================================
    # WEBSOCKET EXECUTION (q:websocket)
    # ============================================

    def _execute_websocket(self, ws_node: WebSocketNode, exec_context: ExecutionContext):
        """
        Execute q:websocket - create WebSocket connection.

        For HTML target, generates client-side JavaScript.
        For server-side, registers connection handlers.
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Get context for databinding
            dict_context = exec_context.to_dict()

            # Resolve URL with databinding
            url = str(self._apply_databinding(ws_node.url, dict_context))

            # Import WebSocket service and adapter
            from runtime.websocket_service import get_websocket_service, WebSocketState
            from runtime.websocket_adapter import get_websocket_html_adapter

            ws_service = get_websocket_service()
            html_adapter = get_websocket_html_adapter()

            # Register connection in service
            connection = ws_service.register_connection(
                name=ws_node.name,
                url=url,
                metadata={
                    "auto_connect": ws_node.auto_connect,
                    "reconnect": ws_node.reconnect,
                    "heartbeat": ws_node.heartbeat
                }
            )

            # Register event handlers
            for handler in ws_node.handlers:
                def create_handler(handler_node):
                    def handler_fn(event_data):
                        # Set event data in context
                        exec_context.set_variable("data", event_data.get("data"), scope="local")
                        exec_context.set_variable("error", event_data.get("error"), scope="local")
                        exec_context.set_variable("event", event_data, scope="local")
                        self.context["data"] = event_data.get("data")
                        self.context["error"] = event_data.get("error")
                        self.context["event"] = event_data

                        # Execute handler body
                        for node in handler_node.body:
                            self._execute_node(node, exec_context)
                    return handler_fn

                ws_service.register_handler(
                    ws_node.name,
                    handler.event,
                    create_handler(handler)
                )

            # Store connection status in context
            status = connection.to_dict()
            exec_context.set_variable(ws_node.name, status, scope="component")
            self.context[ws_node.name] = status

            # For HTML rendering, store the generated JavaScript
            if hasattr(self, '_websocket_scripts'):
                self._websocket_scripts.append(html_adapter.generate_connection(ws_node, dict_context))
            else:
                self._websocket_scripts = [html_adapter.generate_connection(ws_node, dict_context)]

            # Also store manager script (once)
            manager_script = html_adapter.generate_manager_script()
            if manager_script:
                if not hasattr(self, '_websocket_manager_script'):
                    self._websocket_manager_script = manager_script

            logger.info(f"WebSocket '{ws_node.name}' registered: {url}")
            return status

        except Exception as e:
            logger.exception(f"WebSocket execution error: {e}")
            raise ComponentExecutionError(f"WebSocket error: {e}")

    def _execute_websocket_send(self, send_node: WebSocketSendNode, exec_context: ExecutionContext):
        """Execute q:websocket-send - send message through WebSocket."""
        import logging
        logger = logging.getLogger(__name__)

        try:
            dict_context = exec_context.to_dict()

            # Resolve message with databinding
            message = self._apply_databinding(send_node.message, dict_context)

            # Get WebSocket service
            from runtime.websocket_service import get_websocket_service
            ws_service = get_websocket_service()

            # Send message
            success = ws_service.send_message(
                connection_name=send_node.connection,
                data=message,
                msg_type=send_node.type
            )

            if success:
                logger.debug(f"WebSocket send to '{send_node.connection}': {str(message)[:100]}")
            else:
                logger.warning(f"WebSocket send failed - connection '{send_node.connection}' not found or not open")

            return success

        except Exception as e:
            logger.error(f"WebSocket send error: {e}")
            return False

    def _execute_websocket_close(self, close_node: WebSocketCloseNode, exec_context: ExecutionContext):
        """Execute q:websocket-close - close WebSocket connection."""
        import logging
        logger = logging.getLogger(__name__)

        try:
            from runtime.websocket_service import get_websocket_service
            ws_service = get_websocket_service()

            ws_service.close_connection(
                connection_name=close_node.connection,
                code=close_node.code,
                reason=close_node.reason
            )

            logger.info(f"WebSocket '{close_node.connection}' close requested")
            return True

        except Exception as e:
            logger.error(f"WebSocket close error: {e}")
            return False

    # ============================================
    # KNOWLEDGE BASE EXECUTION (q:knowledge + RAG)
    # ============================================

    # Module-level tracking for background knowledge base indexing
    _kb_indexing_status = {}  # {name: 'indexing' | 'ready' | 'failed'}

    def _execute_knowledge(self, knowledge_node: KnowledgeNode, exec_context: ExecutionContext):
        """
        Execute q:knowledge - index documents into ChromaDB.
        Uses background threading to avoid blocking the request.
        """
        import logging
        import threading
        logger = logging.getLogger(__name__)
        kb_name = knowledge_node.name

        # Check indexing status (fast, no I/O)
        status = ComponentRuntime._kb_indexing_status.get(kb_name)

        if status == 'ready':
            exec_context.set_variable(
                f"_knowledge_{kb_name}",
                {"name": kb_name, "model": knowledge_node.model, "embed_model": knowledge_node.embed_model},
                scope="component"
            )
            return

        if status in ('indexing', 'failed'):
            exec_context.set_variable(
                f"_knowledge_{kb_name}",
                {"name": kb_name, "model": knowledge_node.model, "embed_model": knowledge_node.embed_model, "_failed": True},
                scope="component"
            )
            return

        # Skip indexing on this request - just mark as not ready
        ComponentRuntime._kb_indexing_status[kb_name] = 'failed'
        logger.info(f"Knowledge base '{kb_name}' deferred - page will load without RAG")

        exec_context.set_variable(
            f"_knowledge_{kb_name}",
            {"name": kb_name, "model": knowledge_node.model, "embed_model": knowledge_node.embed_model, "_failed": True},
            scope="component"
        )

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
        from runtime.database_service import QueryResult

        try:
            # Extract knowledge base name from datasource
            kb_name = query_node.datasource.replace('knowledge:', '', 1)

            # Check if knowledge base failed to initialize - return empty results
            kb_meta = exec_context.get_variable(f"_knowledge_{kb_name}")
            if isinstance(kb_meta, dict) and kb_meta.get("_failed"):
                from runtime.database_service import QueryResult as _QR
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
    # ============================================

    def _execute_schedule(self, schedule_node: ScheduleNode, exec_context: ExecutionContext):
        """
        Execute q:schedule - Scheduled task execution.

        Supports:
        - action="run": Start/update a scheduled task
        - action="pause": Pause an existing schedule
        - action="resume": Resume a paused schedule
        - action="delete": Remove a schedule

        Examples:
          <q:schedule name="dailyReport" interval="1d">
            <q:query datasource="db" name="stats">SELECT * FROM daily_stats</q:query>
          </q:schedule>

          <q:schedule name="cleanup" cron="0 2 * * *" retry="3" />
        """
        try:
            name = schedule_node.name
            action = schedule_node.action

            if action == 'run':
                # Create schedule callback that executes body statements
                def schedule_callback():
                    # Create child context for schedule execution
                    child_context = exec_context.create_child_context()
                    for statement in schedule_node.body:
                        try:
                            self._execute_statement(statement, child_context)
                        except Exception as e:
                            # Log but continue (schedule will retry if configured)
                            import logging
                            logging.getLogger(__name__).error(
                                f"Schedule '{name}' statement failed: {e}"
                            )
                            raise

                # Add schedule
                schedule_info = self.job_executor.schedule.add_schedule(
                    name=name,
                    callback=schedule_callback,
                    interval=schedule_node.interval,
                    cron=schedule_node.cron,
                    at=schedule_node.at,
                    timezone=schedule_node.timezone,
                    enabled=schedule_node.enabled,
                    overlap=schedule_node.overlap
                )

                # Store schedule info in context
                result = {
                    'name': schedule_info.name,
                    'trigger_type': schedule_info.trigger_type,
                    'trigger_info': schedule_info.trigger_info,
                    'next_run': str(schedule_info.next_run) if schedule_info.next_run else None,
                    'enabled': schedule_info.enabled
                }
                exec_context.set_variable(f"schedule_{name}", result, scope="component")
                self.context[f"schedule_{name}"] = result

                return result

            elif action == 'pause':
                success = self.job_executor.schedule.pause_schedule(name)
                return {'name': name, 'action': 'pause', 'success': success}

            elif action == 'resume':
                success = self.job_executor.schedule.resume_schedule(name)
                return {'name': name, 'action': 'resume', 'success': success}

            elif action == 'delete':
                success = self.job_executor.schedule.remove_schedule(name)
                return {'name': name, 'action': 'delete', 'success': success}

            else:
                raise ComponentExecutionError(f"Invalid schedule action: {action}")

        except ScheduleError as e:
            raise ComponentExecutionError(f"Schedule error in '{schedule_node.name}': {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Schedule execution error in '{schedule_node.name}': {e}")

    def _execute_thread(self, thread_node: ThreadNode, exec_context: ExecutionContext):
        """
        Execute q:thread - Async thread execution.

        Supports:
        - action="run": Start a new background thread
        - action="join": Wait for thread completion
        - action="terminate": Request thread termination

        Examples:
          <q:thread name="sendEmails" priority="high">
            <q:loop query="pendingEmails">
              <q:mail to="{email}" subject="Notification">...</q:mail>
            </q:loop>
          </q:thread>

          <q:thread name="worker1" action="join" />
        """
        try:
            name = thread_node.name
            action = thread_node.action

            if action == 'run':
                # Capture current context for thread execution
                # (copy variables to avoid race conditions)
                thread_context_vars = exec_context.get_all_variables().copy()

                def thread_callback():
                    # Create isolated context for thread
                    from runtime.execution_context import ExecutionContext as EC
                    child_context = EC()
                    for var_name, var_value in thread_context_vars.items():
                        child_context.set_variable(var_name, var_value, scope="component")

                    results = []
                    for statement in thread_node.body:
                        result = self._execute_statement(statement, child_context)
                        if result is not None:
                            results.append(result)

                    return results if results else None

                # Build completion/error callbacks if specified
                on_complete = None
                on_error = None

                if thread_node.on_complete:
                    # Call a function from the function registry
                    func_name = thread_node.on_complete

                    def on_complete_cb(result):
                        func = self.function_registry.get_function(func_name)
                        if func:
                            self._execute_function(func, {'result': result})

                    on_complete = on_complete_cb

                if thread_node.on_error:
                    func_name = thread_node.on_error

                    def on_error_cb(error):
                        func = self.function_registry.get_function(func_name)
                        if func:
                            self._execute_function(func, {'error': str(error)})

                    on_error = on_error_cb

                # Run thread
                thread_info = self.job_executor.thread.run_thread(
                    name=name,
                    callback=thread_callback,
                    priority=thread_node.priority,
                    timeout=thread_node.timeout,
                    on_complete=on_complete,
                    on_error=on_error
                )

                # Store thread info in context
                result = {
                    'name': thread_info.name,
                    'priority': thread_info.priority,
                    'started_at': str(thread_info.started_at),
                    'status': thread_info.status
                }
                exec_context.set_variable(f"thread_{name}", result, scope="component")
                self.context[f"thread_{name}"] = result

                return result

            elif action == 'join':
                # Wait for thread completion
                timeout_seconds = None
                if thread_node.timeout:
                    timeout_seconds = parse_duration(thread_node.timeout)

                try:
                    result = self.job_executor.thread.join_thread(name, timeout=timeout_seconds)

                    # Update thread info
                    thread_info = self.job_executor.thread.get_thread(name)
                    if thread_info:
                        join_result = {
                            'name': thread_info.name,
                            'status': thread_info.status,
                            'result': thread_info.result,
                            'error': thread_info.error
                        }
                        exec_context.set_variable(f"thread_{name}", join_result, scope="component")
                        self.context[f"thread_{name}"] = join_result

                    return result

                except ThreadError as e:
                    raise ComponentExecutionError(f"Thread join failed: {e}")

            elif action == 'terminate':
                success = self.job_executor.thread.terminate_thread(name)
                return {'name': name, 'action': 'terminate', 'success': success}

            else:
                raise ComponentExecutionError(f"Invalid thread action: {action}")

        except ThreadError as e:
            raise ComponentExecutionError(f"Thread error in '{thread_node.name}': {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Thread execution error in '{thread_node.name}': {e}")

    def _execute_job(self, job_node: JobNode, exec_context: ExecutionContext):
        """
        Execute q:job - Job queue for batch processing.

        Supports:
        - action="define": Register a job handler (for later dispatch)
        - action="dispatch": Add job to queue for processing
        - action="batch": Dispatch multiple jobs at once

        Examples:
          <q:job name="sendEmail" queue="emails" priority="5">
            <q:param name="to" type="string" />
            <q:mail to="{to}" subject="Notification">...</q:mail>
          </q:job>

          <q:job name="processOrder" action="dispatch" delay="5m">
            <q:param name="orderId" value="{orderId}" />
          </q:job>
        """
        try:
            name = job_node.name
            action = job_node.action

            if action == 'define':
                # Register job handler
                def job_handler(params: Dict[str, Any]):
                    # Create context with job params
                    from runtime.execution_context import ExecutionContext as EC
                    child_context = EC()
                    for param_name, param_value in params.items():
                        child_context.set_variable(param_name, param_value, scope="component")

                    # Execute job body
                    for statement in job_node.body:
                        self._execute_statement(statement, child_context)

                self.job_executor.job_queue.register_handler(name, job_handler)

                # Start worker for the queue if not already running
                queue = job_node.queue
                self.job_executor.job_queue.start_worker(queue)

                result = {
                    'name': name,
                    'action': 'define',
                    'queue': queue,
                    'success': True
                }
                exec_context.set_variable(f"job_{name}", result, scope="component")
                self.context[f"job_{name}"] = result

                return result

            elif action == 'dispatch':
                # Build params from job params
                params = {}
                context_vars = exec_context.get_all_variables()
                for param in job_node.params:
                    param_value = param.default
                    if param.name in context_vars:
                        param_value = context_vars[param.name]
                    # If param has value attribute, resolve it
                    if hasattr(param, 'value') and param.value:
                        param_value = self._apply_databinding(param.value, context_vars)
                    params[param.name] = param_value

                # Dispatch job
                job_id = self.job_executor.job_queue.dispatch(
                    name=name,
                    queue=job_node.queue,
                    params=params,
                    delay=job_node.delay,
                    priority=job_node.priority,
                    attempts=job_node.attempts,
                    backoff=job_node.backoff
                )

                result = {
                    'job_id': job_id,
                    'name': name,
                    'queue': job_node.queue,
                    'action': 'dispatch',
                    'params': params,
                    'success': True
                }
                exec_context.set_variable(f"dispatched_job_{name}", result, scope="component")
                self.context[f"dispatched_job_{name}"] = result

                return result

            elif action == 'batch':
                # Dispatch multiple jobs - params define the list
                # For now, dispatch a single job with all collected params
                params = {}
                context_vars = exec_context.get_all_variables()
                for param in job_node.params:
                    param_value = param.default
                    if param.name in context_vars:
                        param_value = context_vars[param.name]
                    params[param.name] = param_value

                job_ids = self.job_executor.job_queue.dispatch_batch(
                    jobs=[{'name': name, 'params': params}],
                    queue=job_node.queue
                )

                result = {
                    'job_ids': job_ids,
                    'name': name,
                    'queue': job_node.queue,
                    'action': 'batch',
                    'count': len(job_ids),
                    'success': True
                }
                exec_context.set_variable(f"batch_job_{name}", result, scope="component")
                self.context[f"batch_job_{name}"] = result

                return result

            else:
                raise ComponentExecutionError(f"Invalid job action: {action}")

        except JobQueueError as e:
            raise ComponentExecutionError(f"Job queue error in '{job_node.name}': {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Job execution error in '{job_node.name}': {e}")

    # ============================================
    # MESSAGE QUEUE SYSTEM EXECUTION METHODS
    # ============================================

    def _execute_message(self, message_node: MessageNode, exec_context: ExecutionContext):
        """
        Execute q:message statement for publishing/sending messages.

        Args:
            message_node: MessageNode with message configuration
            exec_context: Execution context for variables

        Returns:
            Result dict with message ID and status
        """
        try:
            dict_context = exec_context.get_all_variables()

            # Resolve topic/queue names with databinding
            topic = None
            queue = None
            if message_node.topic:
                topic = self._apply_databinding(message_node.topic, dict_context)
            if message_node.queue:
                queue = self._apply_databinding(message_node.queue, dict_context)

            # Resolve headers
            headers = {}
            for header in message_node.headers:
                header_name = header.name
                header_value = self._apply_databinding(header.value, dict_context)
                headers[header_name] = str(header_value)

            # Resolve body with databinding
            body = None
            if message_node.body:
                body = self._apply_databinding(message_node.body, dict_context)

            # Execute based on message type
            msg_type = message_node.type

            if msg_type == 'publish' and topic:
                result = self.message_queue_service.publish(
                    topic=topic,
                    body=body,
                    headers=headers
                )
            elif msg_type == 'send' and queue:
                result = self.message_queue_service.send(
                    queue=queue,
                    body=body,
                    headers=headers
                )
            elif msg_type == 'request' and queue:
                timeout = 5000  # Default timeout
                if message_node.timeout:
                    timeout = int(self._apply_databinding(message_node.timeout, dict_context))
                result = self.message_queue_service.request(
                    queue=queue,
                    body=body,
                    headers=headers,
                    timeout=timeout
                )
            else:
                raise ComponentExecutionError(
                    f"Invalid message configuration: type={msg_type}, topic={topic}, queue={queue}"
                )

            # Store result in context if name is specified
            if message_node.name:
                result_dict = result.to_dict()
                exec_context.set_variable(message_node.name, result_dict, scope="component")
                self.context[message_node.name] = result_dict

                # For request type, also store the response data directly
                if msg_type == 'request' and result.data:
                    exec_context.set_variable(f"{message_node.name}.data", result.data, scope="component")
                    self.context[f"{message_node.name}.data"] = result.data

            return result.to_dict()

        except MessageQueueError as e:
            raise ComponentExecutionError(f"Message queue error: {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Message execution error: {e}")

    def _execute_subscribe(self, subscribe_node: SubscribeNode, exec_context: ExecutionContext):
        """
        Execute q:subscribe statement for subscribing to topics or consuming from queues.

        Note: Subscriptions are registered but run asynchronously.
        The on_message and on_error handlers are executed when messages arrive.

        Args:
            subscribe_node: SubscribeNode with subscription configuration
            exec_context: Execution context for variables

        Returns:
            Subscription ID
        """
        try:
            dict_context = exec_context.get_all_variables()

            # Resolve topic/queue names
            topic = None
            topics = None
            queue = None

            if subscribe_node.topic:
                topic = self._apply_databinding(subscribe_node.topic, dict_context)
            if subscribe_node.topics:
                topics = self._apply_databinding(subscribe_node.topics, dict_context)
            if subscribe_node.queue:
                queue = self._apply_databinding(subscribe_node.queue, dict_context)

            # Create handler function for messages
            def message_handler(message_context: dict):
                """Handle incoming message by executing on_message statements."""
                # Create a child context for message processing
                msg_context = exec_context.create_child_context()

                # Add message to context
                msg_context.set_variable('message', message_context, scope="local")

                # Add message fields for convenience
                for key, value in message_context.items():
                    msg_context.set_variable(f"message.{key}", value, scope="local")

                try:
                    # Execute on_message statements
                    for statement in subscribe_node.on_message:
                        self._execute_statement(statement, msg_context)

                except Exception as e:
                    # Execute on_error statements
                    error_context = msg_context
                    error_context.set_variable('error', str(e), scope="local")

                    for statement in subscribe_node.on_error:
                        try:
                            self._execute_statement(statement, error_context)
                        except Exception as inner_e:
                            print(f"[MessageQueue] Error in on_error handler: {inner_e}")

                    # Re-raise if no error handler
                    if not subscribe_node.on_error:
                        raise

            # Register subscription
            subscription_id = self.message_queue_service.subscribe(
                name=subscribe_node.name,
                topic=topic,
                topics=topics,
                queue=queue,
                handler=message_handler,
                ack=subscribe_node.ack,
                prefetch=subscribe_node.prefetch
            )

            # Store subscription info in context
            subscription_info = {
                'id': subscription_id,
                'name': subscribe_node.name,
                'topic': topic,
                'topics': topics,
                'queue': queue,
                'ack': subscribe_node.ack,
                'active': True
            }

            exec_context.set_variable(subscribe_node.name, subscription_info, scope="component")
            self.context[subscribe_node.name] = subscription_info

            return subscription_info

        except MessageQueueError as e:
            raise ComponentExecutionError(f"Subscribe error: {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Subscribe execution error: {e}")

    def _execute_queue(self, queue_node: QueueNode, exec_context: ExecutionContext):
        """
        Execute q:queue statement for queue declaration and management.

        Args:
            queue_node: QueueNode with queue configuration
            exec_context: Execution context for variables

        Returns:
            Result dict based on action
        """
        try:
            dict_context = exec_context.get_all_variables()

            # Resolve queue name
            queue_name = self._apply_databinding(queue_node.name, dict_context)
            action = queue_node.action

            if action == 'declare':
                # Resolve dead letter queue name if specified
                dlq = None
                if queue_node.dead_letter_queue:
                    dlq = self._apply_databinding(queue_node.dead_letter_queue, dict_context)

                result = self.message_queue_service.declare_queue(
                    name=queue_name,
                    durable=queue_node.durable,
                    exclusive=queue_node.exclusive,
                    auto_delete=queue_node.auto_delete,
                    dead_letter_queue=dlq,
                    ttl=queue_node.ttl
                )

            elif action == 'purge':
                result = self.message_queue_service.purge_queue(queue_name)

            elif action == 'delete':
                result = self.message_queue_service.delete_queue(queue_name)

            elif action == 'info':
                result = self.message_queue_service.get_queue_info(queue_name)

                # Store info in result variable
                if queue_node.result and result.success:
                    exec_context.set_variable(queue_node.result, result.data, scope="component")
                    self.context[queue_node.result] = result.data

            else:
                raise ComponentExecutionError(f"Invalid queue action: {action}")

            return result.to_dict()

        except MessageQueueError as e:
            raise ComponentExecutionError(f"Queue error in '{queue_node.name}': {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Queue execution error in '{queue_node.name}': {e}")

    def _execute_message_ack(self, ack_node: MessageAckNode, exec_context: ExecutionContext):
        """
        Execute q:messageAck statement for acknowledging messages.

        This is used inside q:subscribe with ack="manual" to acknowledge
        successful message processing.

        Args:
            ack_node: MessageAckNode
            exec_context: Execution context

        Returns:
            None
        """
        try:
            self.message_queue_service.ack()
        except Exception as e:
            raise ComponentExecutionError(f"Message ack error: {e}")

    def _execute_message_nack(self, nack_node: MessageNackNode, exec_context: ExecutionContext):
        """
        Execute q:messageNack statement for negative acknowledgment.

        This is used inside q:subscribe with ack="manual" to reject a message.

        Args:
            nack_node: MessageNackNode with requeue setting
            exec_context: Execution context

        Returns:
            None
        """
        try:
            self.message_queue_service.nack(requeue=nack_node.requeue)
        except Exception as e:
            raise ComponentExecutionError(f"Message nack error: {e}")

    # =========================================================================
    # Python Scripting System (q:python, q:pyimport, q:class, q:decorator)
    # =========================================================================

    def _execute_python(self, python_node: PythonNode, exec_context: ExecutionContext):
        """
        Execute q:python block with embedded Python code.

        The code has access to the magical 'q' object (QuantumBridge) that provides:
        - Variable access: q.variable, q.variable = value
        - Database: q.query(), q.execute()
        - HTTP: q.get(), q.post()
        - Message queue: q.publish(), q.dispatch()
        - Logging: q.info(), q.warn(), q.error()
        - And more...

        Args:
            python_node: PythonNode with code, scope, async_mode, timeout, result
            exec_context: Execution context

        Returns:
            The result of the Python execution (stored in result variable if specified)
        """
        from runtime.python_bridge import QuantumBridge, QuantumBridgeError

        try:
            # Get the Python code
            code = python_node.code
            if not code or not code.strip():
                return None

            # Build services dict for the bridge
            services = {
                'db': getattr(self, 'database_service', None),
                'cache': getattr(self, 'cache_service', None),
                'broker': getattr(self, 'message_queue_service', None),
                'jobs': getattr(self, 'job_executor', None),
            }

            # Create the bridge (the magical 'q' object)
            q = QuantumBridge(
                context=self.context,
                services=services,
                request=getattr(self, 'request', None)
            )

            # Build the execution namespace
            namespace = {
                'q': q,
                '__builtins__': __builtins__,
                # Inject commonly used imports
                'json': __import__('json'),
                'datetime': __import__('datetime'),
                're': __import__('re'),
                'math': __import__('math'),
            }

            # Add component variables to namespace for direct access
            for key, value in self.context.items():
                if not key.startswith('_'):
                    namespace[key] = value

            # Add imported modules from q:pyimport
            py_modules = exec_context.get_variable('_py_modules')
            if py_modules:
                namespace.update(py_modules)

            # Add defined classes from q:class
            py_classes = exec_context.get_variable('_py_classes')
            if py_classes:
                namespace.update(py_classes)

            # Add defined decorators from q:decorator
            py_decorators = exec_context.get_variable('_py_decorators')
            if py_decorators:
                namespace.update(py_decorators)

            # Execute the code
            if python_node.async_mode:
                # Async execution
                result = self._execute_python_async(code, namespace, python_node.timeout)
            else:
                # Sync execution
                exec(code, namespace)
                result = namespace.get('_result_', None)

            # Sync variables back from 'q' to context
            exports = q._exports
            for key, value in exports.items():
                self.context[key] = value
                exec_context.set_variable(key, value, scope="component")

            # Also sync any variable set via q.variable = value
            for key in dir(q):
                if not key.startswith('_'):
                    try:
                        value = getattr(q, key)
                        if not callable(value):
                            self.context[key] = value
                            exec_context.set_variable(key, value, scope="component")
                    except Exception:
                        pass

            # Store result if specified
            if python_node.result and result is not None:
                self.context[python_node.result] = result
                exec_context.set_variable(python_node.result, result, scope="component")

            return result

        except QuantumBridgeError as e:
            raise ComponentExecutionError(f"Python bridge error: {e}")
        except SyntaxError as e:
            raise ComponentExecutionError(f"Python syntax error: {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Python execution error: {e}")

    def _execute_python_async(self, code: str, namespace: dict, timeout: str = None):
        """
        Execute Python code asynchronously with optional timeout.

        Args:
            code: Python code to execute
            namespace: Execution namespace
            timeout: Optional timeout string (e.g., "30s", "5m")

        Returns:
            Execution result
        """
        import threading
        import asyncio

        result_container = {'result': None, 'error': None}

        def run_code():
            try:
                # Create event loop for async code
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Wrap code in async function if needed
                if 'await ' in code or 'async ' in code:
                    async_code = f"""
async def _async_main():
{chr(10).join('    ' + line for line in code.split(chr(10)))}
    return locals().get('_result_')

import asyncio
_result_ = asyncio.get_event_loop().run_until_complete(_async_main())
"""
                    exec(async_code, namespace)
                else:
                    exec(code, namespace)

                result_container['result'] = namespace.get('_result_')
            except Exception as e:
                result_container['error'] = e
            finally:
                loop.close()

        # Parse timeout
        timeout_seconds = None
        if timeout:
            timeout_seconds = self._parse_timeout(timeout)

        # Run in thread
        thread = threading.Thread(target=run_code)
        thread.start()
        thread.join(timeout=timeout_seconds)

        if thread.is_alive():
            raise ComponentExecutionError(f"Python execution timed out after {timeout}")

        if result_container['error']:
            raise result_container['error']

        return result_container['result']

    def _parse_timeout(self, timeout: str) -> float:
        """Parse timeout string to seconds (e.g., '30s', '5m', '1h')"""
        if not timeout:
            return None

        timeout = timeout.strip().lower()
        multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}

        for suffix, mult in multipliers.items():
            if timeout.endswith(suffix):
                try:
                    return float(timeout[:-1]) * mult
                except ValueError:
                    return None

        try:
            return float(timeout)
        except ValueError:
            return None

    def _execute_pyimport(self, import_node: PyImportNode, exec_context: ExecutionContext):
        """
        Execute q:pyimport statement to import Python modules.

        Examples:
            <q:pyimport module="pandas" alias="pd" />
            <q:pyimport module="numpy" names="array,zeros,ones" />

        Args:
            import_node: PyImportNode with module, alias, names
            exec_context: Execution context

        Returns:
            None (modules are stored for use in q:python blocks)
        """
        try:
            module_name = import_node.module
            alias = import_node.alias
            names = import_node.names

            # Get or create modules dict
            py_modules = exec_context.get_variable('_py_modules')
            if py_modules is None:
                py_modules = {}
                exec_context.set_variable('_py_modules', py_modules, scope="component")

            # Import the module
            module = __import__(module_name, fromlist=names if names else [])

            if names:
                # Import specific names: from module import name1, name2
                for name in names:
                    if hasattr(module, name):
                        py_modules[name] = getattr(module, name)
                    else:
                        raise ComponentExecutionError(
                            f"Cannot import '{name}' from module '{module_name}'"
                        )
            else:
                # Import module with optional alias
                key = alias if alias else module_name.split('.')[0]
                py_modules[key] = module

            # Update stored modules
            exec_context.set_variable('_py_modules', py_modules, scope="component")

        except ImportError as e:
            raise ComponentExecutionError(f"Python import error: {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Python import error: {e}")

    def _execute_pyclass(self, class_node: PyClassNode, exec_context: ExecutionContext):
        """
        Execute q:class statement to define a Python class.

        Example:
            <q:class name="UserValidator" bases="BaseValidator">
                def validate(self, data):
                    return data.get('email') and '@' in data['email']
            </q:class>

        Args:
            class_node: PyClassNode with name, code, bases, decorators
            exec_context: Execution context

        Returns:
            None (class is stored for use in q:python blocks)
        """
        try:
            class_name = class_node.name
            code = class_node.code
            bases = class_node.bases or []
            decorators = class_node.decorators or []

            # Get or create classes dict
            py_classes = exec_context.get_variable('_py_classes')
            if py_classes is None:
                py_classes = {}
                exec_context.set_variable('_py_classes', py_classes, scope="component")

            # Get modules and existing classes for resolution
            py_modules = exec_context.get_variable('_py_modules') or {}
            py_decorators = exec_context.get_variable('_py_decorators') or {}

            # Build namespace for class definition
            namespace = {
                '__builtins__': __builtins__,
                **py_modules,
                **py_classes,
                **py_decorators,
            }

            # Resolve base classes
            base_classes = []
            for base in bases:
                if base in namespace:
                    base_classes.append(namespace[base])
                elif base == 'object':
                    base_classes.append(object)
                else:
                    raise ComponentExecutionError(f"Unknown base class: {base}")

            if not base_classes:
                base_classes = [object]

            # Build class definition
            indent = "    "
            class_body = '\n'.join(indent + line for line in code.strip().split('\n'))

            decorator_str = ''
            for dec in decorators:
                decorator_str += f"@{dec}\n"

            bases_str = ', '.join(bases) if bases else 'object'
            class_def = f"{decorator_str}class {class_name}({bases_str}):\n{class_body}"

            # Execute class definition
            exec(class_def, namespace)

            # Store the class
            py_classes[class_name] = namespace[class_name]
            exec_context.set_variable('_py_classes', py_classes, scope="component")

        except SyntaxError as e:
            raise ComponentExecutionError(f"Python class syntax error: {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Python class error: {e}")

    def _execute_pydecorator(self, decorator_node: PyDecoratorNode, exec_context: ExecutionContext):
        """
        Execute q:decorator statement to define a Python decorator.

        Example:
            <q:decorator name="cached" params="ttl">
                def decorator(func):
                    cache = {}
                    def wrapper(*args, **kwargs):
                        key = str(args) + str(kwargs)
                        if key not in cache:
                            cache[key] = func(*args, **kwargs)
                        return cache[key]
                    return wrapper
                return decorator
            </q:decorator>

        Args:
            decorator_node: PyDecoratorNode with name, code, params
            exec_context: Execution context

        Returns:
            None (decorator is stored for use in q:python and q:class blocks)
        """
        try:
            decorator_name = decorator_node.name
            code = decorator_node.code
            params = decorator_node.params or []

            # Get or create decorators dict
            py_decorators = exec_context.get_variable('_py_decorators')
            if py_decorators is None:
                py_decorators = {}
                exec_context.set_variable('_py_decorators', py_decorators, scope="component")

            # Get modules for resolution
            py_modules = exec_context.get_variable('_py_modules') or {}

            # Build namespace
            namespace = {
                '__builtins__': __builtins__,
                **py_modules,
            }

            # Build decorator function
            params_str = ', '.join(params) if params else ''
            indent = "    "
            decorator_body = '\n'.join(indent + line for line in code.strip().split('\n'))

            if params:
                # Parameterized decorator
                decorator_def = f"def {decorator_name}({params_str}):\n{decorator_body}"
            else:
                # Simple decorator
                decorator_def = f"def {decorator_name}(func):\n{decorator_body}"

            # Execute decorator definition
            exec(decorator_def, namespace)

            # Store the decorator
            py_decorators[decorator_name] = namespace[decorator_name]
            exec_context.set_variable('_py_decorators', py_decorators, scope="component")

        except SyntaxError as e:
            raise ComponentExecutionError(f"Python decorator syntax error: {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Python decorator error: {e}")
