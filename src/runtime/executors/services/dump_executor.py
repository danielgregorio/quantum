"""
Dump Executor - Execute q:dump statements

Handles variable inspection and debugging output.
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError
from core.features.dump.src import DumpNode


class DumpExecutor(BaseExecutor):
    """
    Executor for q:dump statements.

    Supports:
    - Variable inspection with depth control
    - Multiple output formats (text, json, html)
    - Conditional dumping
    - Labeled output
    """

    @property
    def handles(self) -> List[Type]:
        return [DumpNode]

    def execute(self, node: DumpNode, exec_context) -> Any:
        """
        Execute variable dump/inspection.

        Args:
            node: DumpNode with dump configuration
            exec_context: Execution context

        Returns:
            Formatted dump output string
        """
        try:
            context = exec_context.get_all_variables()

            # Check conditional execution
            if node.when:
                condition_result = self.apply_databinding(node.when, context)
                if not self.services.dump.should_dump(condition_result):
                    return

            # Resolve variable to dump
            var_expr = node.var
            try:
                var_value = self.apply_databinding(var_expr, context)
            except Exception as e:
                var_value = f"<Variable '{var_expr}' not found: {e}>"

            # Generate dump output
            dump_output = self.services.dump.dump(
                var=var_value,
                label=node.label,
                format=node.format,
                depth=node.depth
            )

            # Print dump output
            print(dump_output)

            # Store in context for potential template rendering
            dump_var_name = f"_dump_{node.label.replace(' ', '_')}"
            exec_context.set_variable(dump_var_name, dump_output, scope="component")

            return dump_output

        except Exception as e:
            raise ExecutorError(f"Dump error: {e}")
