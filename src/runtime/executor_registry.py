"""
Executor Registry - Central dispatch for node execution

Replaces the large if-elif chain in component.py with a type-based lookup.
Executors register themselves for specific node types, and the registry
dispatches execution to the correct executor.
"""

from typing import Dict, Type, Any, Optional, List, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from runtime.executors.base import BaseExecutor
    from runtime.execution_context import ExecutionContext

logger = logging.getLogger(__name__)


class ExecutorNotFoundError(Exception):
    """Raised when no executor is registered for a node type"""
    pass


class ExecutorRegistry:
    """
    Registry for node executors.

    Maps AST node types to their executors and dispatches execution.

    Example:
        registry = ExecutorRegistry()
        registry.register(LoopExecutor(runtime))
        registry.register(IfExecutor(runtime))

        # Later, execute any node
        result = registry.execute(loop_node, context)
    """

    def __init__(self):
        """Initialize empty registry"""
        self._executors: Dict[Type, 'BaseExecutor'] = {}
        self._fallback: Optional['BaseExecutor'] = None

    def register(self, executor: 'BaseExecutor') -> 'ExecutorRegistry':
        """
        Register an executor for its handled node types.

        Args:
            executor: Executor instance to register

        Returns:
            Self for chaining
        """
        for node_type in executor.handles:
            if node_type in self._executors:
                logger.warning(
                    f"Overwriting executor for {node_type.__name__}: "
                    f"{self._executors[node_type].__class__.__name__} -> "
                    f"{executor.__class__.__name__}"
                )
            self._executors[node_type] = executor
            logger.debug(f"Registered {executor.__class__.__name__} for {node_type.__name__}")

        return self

    def register_all(self, executors: List['BaseExecutor']) -> 'ExecutorRegistry':
        """
        Register multiple executors at once.

        Args:
            executors: List of executor instances

        Returns:
            Self for chaining
        """
        for executor in executors:
            self.register(executor)
        return self

    def set_fallback(self, executor: 'BaseExecutor') -> 'ExecutorRegistry':
        """
        Set a fallback executor for unregistered node types.

        Args:
            executor: Fallback executor instance

        Returns:
            Self for chaining
        """
        self._fallback = executor
        return self

    def get_executor(self, node: Any) -> Optional['BaseExecutor']:
        """
        Get the executor for a node.

        Args:
            node: AST node instance

        Returns:
            Executor instance or None if not found
        """
        node_type = type(node)
        return self._executors.get(node_type)

    def has_executor(self, node_type: Type) -> bool:
        """
        Check if an executor is registered for a node type.

        Args:
            node_type: AST node class

        Returns:
            True if executor exists
        """
        return node_type in self._executors

    def execute(self, node: Any, exec_context: 'ExecutionContext') -> Any:
        """
        Execute a node using its registered executor.

        Args:
            node: AST node to execute
            exec_context: Execution context

        Returns:
            Result of execution

        Raises:
            ExecutorNotFoundError: If no executor is registered for the node type
        """
        node_type = type(node)
        executor = self._executors.get(node_type)

        if executor is None:
            if self._fallback is not None:
                logger.debug(f"Using fallback executor for {node_type.__name__}")
                return self._fallback.execute(node, exec_context)

            raise ExecutorNotFoundError(
                f"No executor registered for {node_type.__name__}. "
                f"Registered types: {list(t.__name__ for t in self._executors.keys())}"
            )

        return executor.execute(node, exec_context)

    def can_execute(self, node: Any) -> bool:
        """
        Check if a node can be executed.

        Args:
            node: AST node instance

        Returns:
            True if an executor exists for this node type
        """
        return type(node) in self._executors or self._fallback is not None

    @property
    def registered_types(self) -> List[Type]:
        """Get list of all registered node types"""
        return list(self._executors.keys())

    @property
    def executor_count(self) -> int:
        """Get number of registered executors (unique)"""
        return len(set(self._executors.values()))

    def __repr__(self) -> str:
        types = [t.__name__ for t in self._executors.keys()]
        return f"ExecutorRegistry({len(types)} types: {types[:5]}{'...' if len(types) > 5 else ''})"
