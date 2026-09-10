"""
Loop Executor - Execute q:loop statements

Handles all loop types: range, array, list, query.
"""

from typing import Any, List, Dict, Type
import json
from quantum.runtime.executors.base import BaseExecutor, ExecutorError
from quantum.core.features.loops.src.ast_node import LoopNode
from quantum.core.features.conditionals.src.ast_node import IfNode
from quantum.core.features.state_management.src.ast_node import SetNode
from quantum.core.features.logging.src import LogNode
from quantum.core.features.dump.src import DumpNode
from quantum.core.ast_nodes import (
    QuantumReturn,
    HTMLNode, TextNode, DocTypeNode, CommentNode,
    ActionNode, RedirectNode, FlashNode, ImportNode, SlotNode, FunctionNode,
)

# Render-only / special-purpose nodes that never go through the executor
# registry (see component.py's top-level _execute_statement, which skips the
# same types). A loop body with plain text content used to raise
# "No executor registered for TextNode" — reachable only once the loop-type
# inference bug in loop_parser.py was fixed, since before that such bodies
# never parsed as array/list/query loops in the first place.
_RENDER_ONLY_NODE_TYPES = (
    HTMLNode, TextNode, DocTypeNode, CommentNode,
    ActionNode, RedirectNode, FlashNode, ImportNode, SlotNode, FunctionNode,
)


class LoopReturns(list):
    """Os valores dos q:return executados dentro de um q:loop, em ordem.

    Um tipo proprio, e nao `list`, porque o resultado de um loop antes
    misturava qualquer coisa nao-None que o corpo produzisse — linhas de um
    q:query, por exemplo — e por isso quem chamava nao tinha como tratar o
    loop como return e simplesmente jogava o resultado fora. Era assim que
    `<q:loop ...><q:return value="{x}"/></q:loop>` num componente devolvia
    None, contra o que getting-started.md documenta.
    """


def produced_return(statement, result) -> bool:
    """O statement executado deve encerrar o corpo que o contem?

    Vale para um q:if cujo ramo executou um q:return, e para um q:loop que
    coletou pelo menos um. Um loop que nao coletou nada — so q:set, ou um
    filtro que nao casou — deixa a execucao seguir, como um q:if falso.
    """
    if isinstance(result, LoopReturns):
        return len(result) > 0
    return result is not None and isinstance(statement, IfNode)


def as_return_value(result):
    """Entrega um LoopReturns como lista comum para quem esta fora do runtime."""
    return list(result) if isinstance(result, LoopReturns) else result


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
        results = LoopReturns()
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
                    self._collect(results, statement, result)

            return results

        except (ValueError, TypeError) as e:
            raise ExecutorError(f"Range loop error: {e}")

    def _execute_array(self, node: LoopNode, exec_context) -> List:
        """Execute array loop"""
        results = LoopReturns()
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
                    self._collect(results, statement, result)
                    loop_context = exec_context.get_all_variables()

            return results

        except Exception as e:
            raise ExecutorError(f"Array loop error: {e}")

    def _execute_list(self, node: LoopNode, exec_context) -> List:
        """Execute list loop (delimited string)"""
        results = LoopReturns()
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
                    self._collect(results, statement, result)

            return results

        except Exception as e:
            raise ExecutorError(f"List loop error: {e}")

    def _execute_query(self, node: LoopNode, exec_context) -> List:
        """Execute query loop - iterate over query result rows"""
        results = LoopReturns()
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
                    self._collect(results, statement, result)

            return results

        except Exception as e:
            raise ExecutorError(f"Query loop error: {e}")

    @staticmethod
    def _collect(results: LoopReturns, statement, result) -> None:
        """Guarda em `results` o que o statement retornou, e so isso.

        Cada q:return executado vira um item — inclusive os de um loop
        aninhado, que entram soltos, na ordem (docs/guide/loops.md, "Nested
        Loops"). Um q:if cujo ramo retornou vira um item. O resto (linhas de
        q:query, valores de q:set etc.) nao e return e nao entra.

        So LoopReturns e achatado: `<q:return value="{lista}"/>` continua
        sendo UM item, mesmo sendo uma lista.
        """
        if isinstance(statement, QuantumReturn):
            if result is not None:
                results.append(result)
        elif isinstance(result, LoopReturns):
            results.extend(result)
        elif produced_return(statement, result):
            results.append(result)

    def _execute_body_statement(self, statement, context: Dict[str, Any], exec_context) -> Any:
        """Execute a statement inside a loop body"""
        if isinstance(statement, QuantumReturn):
            return self.resolve_value(statement.value, context)
        elif isinstance(statement, _RENDER_ONLY_NODE_TYPES):
            # Text/HTML content is handled by HTMLRenderer._render_loop(),
            # which independently re-iterates and renders the body — it is
            # not meant to be executed here.
            return None
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
