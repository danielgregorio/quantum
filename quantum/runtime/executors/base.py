"""
Base Executor - Abstract base class for all node executors

All executors inherit from BaseExecutor and implement the execute() method.
The ExecutorRegistry uses the 'handles' property to dispatch nodes to the correct executor.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Type, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from quantum.runtime.execution_context import ExecutionContext


class ExecutorError(Exception):
    """Base exception for executor errors"""
    pass


class BaseExecutor(ABC):
    """
    Abstract base class for all node executors.

    Each executor handles one or more AST node types and implements
    the execute() method to process them.

    Example:
        class LoopExecutor(BaseExecutor):
            @property
            def handles(self) -> List[Type]:
                return [LoopNode]

            def execute(self, node: LoopNode, context: ExecutionContext) -> Any:
                # Execute loop logic
                pass
    """

    def __init__(self, runtime: 'ComponentRuntime'):
        """
        Initialize executor with reference to runtime.

        Args:
            runtime: The ComponentRuntime instance (provides services and context)
        """
        self._runtime = runtime

    @property
    def runtime(self) -> 'ComponentRuntime':
        """Access to the component runtime"""
        return self._runtime

    @property
    def context(self) -> 'ExecutionContext':
        """Shortcut to execution context"""
        return self._runtime.execution_context

    @property
    def services(self) -> 'ServiceContainer':
        """Shortcut to service container"""
        return self._runtime.services

    @property
    @abstractmethod
    def handles(self) -> List[Type]:
        """
        List of AST node types this executor handles.

        Returns:
            List of node classes (e.g., [LoopNode, ForNode])
        """
        pass

    @abstractmethod
    def execute(self, node: Any, exec_context: 'ExecutionContext') -> Any:
        """
        Execute the node and return result.

        Args:
            node: The AST node to execute
            exec_context: The execution context with variables and scopes

        Returns:
            The result of execution (type depends on node type)
        """
        pass

    # ==========================================================================
    # Helper methods - Common utilities available to all executors
    # ==========================================================================

    def apply_databinding(self, value: str, context: Dict[str, Any] = None) -> Any:
        """
        Apply databinding to resolve {variable} expressions.

        Args:
            value: String potentially containing {expressions}
            context: Variable context (uses exec_context if not provided)

        Returns:
            Resolved value
        """
        if context is None:
            context = self.get_all_variables()
        return self._runtime._apply_databinding(value, context)

    def evaluate_condition(self, condition: str, context: Dict[str, Any] = None) -> bool:
        """
        Evaluate a condition string.

        Args:
            condition: Condition expression (e.g., "{x} > 5")
            context: Variable context

        Returns:
            Boolean result
        """
        if context is None:
            context = self.get_all_variables()
        return self._runtime._evaluate_condition(condition, context)

    def get_all_variables(self) -> Dict[str, Any]:
        """
        Get all variables from execution context.

        Returns:
            Dict of all variables across all scopes
        """
        return self.context.get_all_variables()

    def set_variable(self, name: str, value: Any, scope: str = "local"):
        """
        Set a variable in the execution context.

        Args:
            name: Variable name
            value: Variable value
            scope: Scope (local, component, session, application)
        """
        self.context.set_variable(name, value, scope=scope)

    def get_variable(self, name: str, default: Any = None) -> Any:
        """
        Get a variable from the execution context.

        Args:
            name: Variable name
            default: Default value if not found

        Returns:
            Variable value or default
        """
        try:
            return self.context.get_variable(name)
        except Exception:
            return default

    def execute_child(self, node: Any, exec_context: 'ExecutionContext' = None) -> Any:
        """
        Execute a child node using the registry.

        Args:
            node: Child AST node
            exec_context: Execution context (uses self.context if not provided)

        Returns:
            Result of child execution
        """
        if exec_context is None:
            exec_context = self.context
        return self._runtime.executor_registry.execute(node, exec_context)

    def execute_children(self, nodes: List[Any], exec_context: 'ExecutionContext' = None) -> List[Any]:
        """
        Execute multiple child nodes.

        Args:
            nodes: List of AST nodes
            exec_context: Execution context

        Returns:
            List of results
        """
        results = []
        for node in nodes:
            result = self.execute_child(node, exec_context)
            if result is not None:
                results.append(result)
        return results

    def require_python_scripting(self, tag: str):
        """Refuse to run in-process Python when policy disables it.

        q:python/q:pyclass/q:pyimport execute arbitrary Python in the server
        process — no sandbox, full access to the filesystem, network and os.
        That is a deliberate escape hatch for author-written code, but it
        must be switchable off before anything the author did not write
        (LLM-generated templates, user-submitted components) can reach it.
        """
        if not self.services.python_scripting_enabled:
            # A mensagem tem de dizer COMO ligar. O default virou desligado,
            # entao esta e a primeira coisa que quem usa q:python encontra —
            # e um erro que so diz "desabilitado" manda a pessoa procurar no
            # codigo qual e a chave.
            raise ExecutorError(
                f"{tag} is off: security.python_scripting is not enabled. It "
                f"executes arbitrary Python in the server process with no "
                f"sandbox, so it is off by default — turn it on only for "
                f"code you wrote yourself.\n"
                f"  In quantum.config.yaml:\n"
                f"      security:\n"
                f"        python_scripting: true\n"
                f"  Or in the environment: QUANTUM_PYTHON_SCRIPTING=1"
            )

    def run_body_in_child_context(self, body: List[Any], variables: Dict[str, Any] = None) -> Any:
        """
        Execute a list of AST statements in a fresh child context.

        Used by nodes whose body runs detached from the surrounding flow
        (q:schedule callbacks, q:thread callbacks, q:agent tool bodies).
        Render-only nodes are skipped — they belong to HTMLRenderer, not the
        executor registry. Returns the first q:return value found, if any.
        """
        from quantum.core.ast_nodes import (
            QuantumReturn, HTMLNode, TextNode, DocTypeNode, CommentNode,
        )
        render_only = (HTMLNode, TextNode, DocTypeNode, CommentNode)

        child_context = self.context.create_child_context()
        for key, value in (variables or {}).items():
            child_context.set_variable(key, value, scope="local")

        for statement in body or []:
            if isinstance(statement, QuantumReturn):
                return self.resolve_value(
                    statement.value, child_context.get_all_variables()
                )
            if isinstance(statement, render_only):
                continue
            self._runtime.executor_registry.execute(statement, child_context)

        return None

    def resolve_value(self, value: str, context: Dict[str, Any] = None) -> Any:
        """
        Resolve a value string to its actual value.

        Handles:
        - Databinding: {variable}
        - Literals: "string", 123, true/false
        - JSON: {"key": "value"}

        Args:
            value: Value string to resolve
            context: Variable context

        Returns:
            Resolved value
        """
        if context is None:
            context = self.get_all_variables()
        return self._runtime._process_return_value(value, context)
