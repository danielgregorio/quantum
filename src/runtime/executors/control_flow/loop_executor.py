"""
Loop Executor - Execute q:loop statements

Handles all loop types: range, array, list, query.
"""

from typing import Any, List, Dict, Type
import json
from runtime.executors.base import BaseExecutor, ExecutorError
from core.features.loops.src.ast_node import LoopNode
from core.features.conditionals.src.ast_node import IfNode
from core.features.state_management.src.ast_node import SetNode
from core.features.logging.src import LogNode
from core.features.dump.src import DumpNode
from core.ast_nodes import QuantumReturn


class LoopExecutor(BaseExecutor):
    """
    Executor for q:loop statements.

    Supports:
    - range: numeric iteration (from/to/step)
    - array: iterate over array items
    - list: iterate over delimited string
    - query: iterate over query result rows
    """

    @property
    def handles(self) -> List[Type]:
        return [LoopNode]

    def execute(self, node: LoopNode, exec_context) -> Any:
        """
        Execute q:loop statement based on type.

        Args:
            node: LoopNode to execute
            exec_context: Execution context

        Returns:
            List of results from loop iterations
        """
        if node.loop_type == 'range':
            return self._execute_range(node, exec_context)
        elif node.loop_type == 'array':
            return self._execute_array(node, exec_context)
        elif node.loop_type == 'list':
            return self._execute_list(node, exec_context)
        elif node.loop_type == 'query':
            return self._execute_query(node, exec_context)
        else:
            raise ExecutorError(f"Unsupported loop type: {node.loop_type}")

    def _execute_range(self, node: LoopNode, exec_context) -> List:
        """Execute range loop (from/to/step)"""
        results = []
        context = self.get_all_variables()

        try:
            start = int(self._evaluate_simple_expr(node.from_value, context))
            end = int(self._evaluate_simple_expr(node.to_value, context))
            step = node.step_value

            for i in range(start, end + 1, step):
                # Update loop variable
                loop_context = context.copy()
                loop_context[node.var_name] = i
                exec_context.set_variable(node.var_name, i, scope="local")

                # Execute body
                for statement in node.body:
                    result = self._execute_body_statement(statement, loop_context, exec_context)
                    if result is not None:
                        results.append(result)

            return results

        except (ValueError, TypeError) as e:
            raise ExecutorError(f"Range loop error: {e}")

    def _execute_array(self, node: LoopNode, exec_context) -> List:
        """Execute array loop"""
        results = []
        context = self.get_all_variables()

        try:
            array_data = self._parse_array_items(node.items, context)

            for index, item in enumerate(array_data):
                exec_context.set_variable(node.var_name, item, scope="local")

                if node.index_name:
                    exec_context.set_variable(node.index_name, index, scope="local")

                loop_context = exec_context.get_all_variables()

                for statement in node.body:
                    result = self._execute_body_statement(statement, loop_context, exec_context)
                    if result is not None:
                        results.append(result)
                    loop_context = exec_context.get_all_variables()

            return results

        except Exception as e:
            raise ExecutorError(f"Array loop error: {e}")

    def _execute_list(self, node: LoopNode, exec_context) -> List:
        """Execute list loop (delimited string)"""
        results = []
        context = self.get_all_variables()

        try:
            list_data = self._parse_list_items(node.items, node.delimiter, context)

            for index, item in enumerate(list_data):
                loop_context = context.copy()
                loop_context[node.var_name] = item.strip()
                exec_context.set_variable(node.var_name, item.strip(), scope="local")

                if node.index_name:
                    loop_context[node.index_name] = index
                    exec_context.set_variable(node.index_name, index, scope="local")

                for statement in node.body:
                    result = self._execute_body_statement(statement, loop_context, exec_context)
                    if result is not None:
                        results.append(result)

            return results

        except Exception as e:
            raise ExecutorError(f"List loop error: {e}")

    def _execute_query(self, node: LoopNode, exec_context) -> List:
        """Execute query loop - iterate over query result rows"""
        results = []
        context = self.get_all_variables()

        try:
            query_name = node.query_name if hasattr(node, 'query_name') else node.var_name
            query_data = context.get(query_name)

            if query_data is None:
                query_data = exec_context.get_variable(query_name)

            if not query_data:
                raise ExecutorError(f"Query '{query_name}' not found in context")

            if not isinstance(query_data, list):
                raise ExecutorError(f"Query '{query_name}' is not iterable")

            for index, row in enumerate(query_data):
                loop_context = context.copy()

                # Make row fields accessible
                if isinstance(row, dict):
                    for field_name, field_value in row.items():
                        dotted_key = f"{query_name}.{field_name}"
                        loop_context[dotted_key] = field_value
                        exec_context.set_variable(dotted_key, field_value, scope="local")
                        loop_context[field_name] = field_value
                        exec_context.set_variable(field_name, field_value, scope="local")

                loop_context['currentRow'] = row
                exec_context.set_variable('currentRow', row, scope="local")

                if node.index_name:
                    loop_context[node.index_name] = index
                    exec_context.set_variable(node.index_name, index, scope="local")

                for statement in node.body:
                    result = self._execute_body_statement(statement, loop_context, exec_context)
                    if result is not None:
                        results.append(result)

            return results

        except Exception as e:
            raise ExecutorError(f"Query loop error: {e}")

    def _execute_body_statement(self, statement, context: Dict[str, Any], exec_context) -> Any:
        """Execute a statement inside a loop body"""
        if isinstance(statement, QuantumReturn):
            return self.resolve_value(statement.value, context)
        else:
            # Use registry for all other statements
            return self.execute_child(statement, exec_context)

    def _evaluate_simple_expr(self, expr: str, context: Dict[str, Any]) -> Any:
        """Evaluate simple numeric expression"""
        if not expr:
            return 0

        try:
            return int(expr)
        except ValueError:
            try:
                return float(expr)
            except ValueError:
                return context.get(expr, expr)

    def _parse_array_items(self, items_expr: str, context: Dict[str, Any]) -> list:
        """Parse array items from expression"""
        if not items_expr:
            return []

        # Apply databinding
        if '{' in items_expr and '}' in items_expr:
            resolved = self.apply_databinding(items_expr, context)
            if isinstance(resolved, list):
                return resolved
            items_expr = str(resolved) if not isinstance(resolved, str) else resolved

        # Handle JSON array notation
        if items_expr.startswith('[') and items_expr.endswith(']'):
            try:
                return json.loads(items_expr)
            except json.JSONDecodeError:
                items_str = items_expr[1:-1]
                return [item.strip().strip('"\'') for item in items_str.split(',') if item.strip()]

        # Variable reference
        if items_expr in context:
            return context[items_expr]

        return [items_expr]

    def _parse_list_items(self, items_expr: str, delimiter: str, context: Dict[str, Any]) -> list:
        """Parse list items from delimited string"""
        if not items_expr:
            return []

        if items_expr in context:
            items_value = context[items_expr]
            if isinstance(items_value, list):
                return items_value
            elif isinstance(items_value, str):
                return items_value.split(delimiter)

        return items_expr.split(delimiter)
