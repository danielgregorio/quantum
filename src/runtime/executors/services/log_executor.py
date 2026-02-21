"""
Log Executor - Execute q:log statements

Handles structured logging with levels and context.
"""

from typing import Any, List, Dict, Type
import json
from runtime.executors.base import BaseExecutor, ExecutorError
from core.features.logging.src import LogNode


class LogExecutor(BaseExecutor):
    """
    Executor for q:log statements.

    Supports:
    - Multiple log levels (debug, info, warn, error)
    - Conditional logging (when attribute)
    - Context data attachment
    - Correlation IDs for tracing
    """

    @property
    def handles(self) -> List[Type]:
        return [LogNode]

    def execute(self, node: LogNode, exec_context) -> Any:
        """
        Execute logging statement.

        Args:
            node: LogNode with logging configuration
            exec_context: Execution context

        Returns:
            None (logging is side-effect only)
        """
        try:
            context = exec_context.get_all_variables()

            # Check conditional execution
            if node.when:
                condition_result = self.apply_databinding(node.when, context)
                if not self.services.logging.should_log(condition_result):
                    return

            # Resolve message
            message = self.apply_databinding(node.message, context)

            # Resolve context data
            context_data = None
            if node.context:
                context_expr = self.apply_databinding(node.context, context)
                if isinstance(context_expr, dict):
                    context_data = context_expr
                elif isinstance(context_expr, str):
                    try:
                        context_data = json.loads(context_expr)
                    except:
                        context_data = {'value': context_expr}

            # Resolve correlation_id
            correlation_id = None
            if node.correlation_id:
                correlation_id = self.apply_databinding(node.correlation_id, context)

            # Execute logging
            self.services.logging.log(
                level=node.level,
                message=str(message),
                context=context_data,
                correlation_id=correlation_id
            )

        except Exception as e:
            raise ExecutorError(f"Logging error: {e}")
