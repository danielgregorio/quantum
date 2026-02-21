"""
If Executor - Execute q:if statements

Handles conditional execution with elseif and else blocks.
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError
from core.features.conditionals.src.ast_node import IfNode
from core.ast_nodes import QuantumReturn


class IfExecutor(BaseExecutor):
    """
    Executor for q:if statements.

    Supports:
    - Simple if conditions
    - Multiple elseif blocks
    - Optional else block
    - Nested conditionals
    """

    @property
    def handles(self) -> List[Type]:
        return [IfNode]

    def execute(self, node: IfNode, exec_context) -> Any:
        """
        Execute q:if statement with elseif and else.

        Args:
            node: IfNode to execute
            exec_context: Execution context

        Returns:
            Result of executed branch, or None
        """
        context = self.get_all_variables()

        # Evaluate main if condition
        if self.evaluate_condition(node.condition, context):
            return self._execute_body(node.if_body, context)

        # Check elseif conditions
        for elseif_block in node.elseif_blocks:
            if self.evaluate_condition(elseif_block["condition"], context):
                return self._execute_body(elseif_block["body"], context)

        # Execute else block if present
        if node.else_body:
            return self._execute_body(node.else_body, context)

        return None

    def _execute_body(self, statements: List, context: Dict[str, Any]) -> Any:
        """
        Execute a list of statements in a branch body.

        Args:
            statements: List of AST nodes to execute
            context: Variable context

        Returns:
            Return value if any statement returns, None otherwise
        """
        for statement in statements:
            if isinstance(statement, QuantumReturn):
                return self.resolve_value(statement.value, context)
            else:
                # Use registry to execute child statements
                result = self.execute_child(statement)
                # If child is an IfNode and returns something, propagate it
                if result is not None and isinstance(statement, IfNode):
                    return result

        return None
