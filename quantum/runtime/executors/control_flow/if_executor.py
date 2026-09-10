"""
If Executor - Execute q:if statements

Handles conditional execution with elseif and else blocks.
"""

from typing import Any, List, Dict, Type
from quantum.runtime.executors.base import BaseExecutor, ExecutorError
from quantum.runtime.executors.control_flow.loop_executor import produced_return
from quantum.core.features.conditionals.src.ast_node import IfNode
from quantum.core.ast_nodes import (
    QuantumReturn,
    HTMLNode, TextNode, DocTypeNode, CommentNode,
    ActionNode, RedirectNode, FlashNode, ImportNode, SlotNode, FunctionNode,
)

# Same render-only skip list as component.py's top-level _execute_statement
# and loop_executor.py — text/HTML inside a q:if body is handled by
# HTMLRenderer, not by the executor registry.
_RENDER_ONLY_NODE_TYPES = (
    HTMLNode, TextNode, DocTypeNode, CommentNode,
    ActionNode, RedirectNode, FlashNode, ImportNode, SlotNode, FunctionNode,
)


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
            elif isinstance(statement, _RENDER_ONLY_NODE_TYPES):
                continue
            else:
                # Use registry to execute child statements
                result = self.execute_child(statement)
                # A nested q:if that returned, or a q:loop that collected
                # returns, ends this branch with that value.
                if produced_return(statement, result):
                    return result

        return None
