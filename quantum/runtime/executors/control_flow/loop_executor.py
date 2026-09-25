"""
Loop Executor - Execute q:loop statements

Handles all loop types: range, array, list, query.
"""

from typing import Any, List, Dict, Type
import json
from quantum.core.features.ui_engine.src.ast_nodes import is_ui_node
from quantum.runtime.executors.base import BaseExecutor, ExecutorError
from quantum.core.features.loops.src.ast_node import LoopNode
from quantum.core.features.conditionals.src.ast_node import IfNode
from quantum.core.ast_nodes import (
    QuantumReturn,
    HTMLNode, TextNode, DocTypeNode, CommentNode,
    ActionNode, FlashNode, ImportNode, SlotNode, FunctionNode,
)

# Render-only / special-purpose nodes that never go through the executor
# registry (see component.py's top-level _execute_statement, which skips the
# same types). A loop body with plain text content used to raise
# "No executor registered for TextNode" — reachable only once the loop-type
# inference bug in loop_parser.py was fixed, since before that such bodies
# never parsed as array/list/query loops in the first place.
_RENDER_ONLY_NODE_TYPES = (
    HTMLNode, TextNode, DocTypeNode, CommentNode,
    ActionNode, FlashNode, ImportNode, SlotNode, FunctionNode,
)


class LoopReturns(list):
    """The values of the q:return statements executed inside a q:loop, in order.

    A type of its own, and not `list`, because the result of a loop used to
    mix in anything non-None the body produced — rows of a q:query, for
    example — and so the caller had no way to treat the loop as a return
    and simply threw the result away. That is how
    `<q:loop ...><q:return value="{x}"/></q:loop>` in a component returned
    None, contrary to what getting-started.md documents.
    """


def produced_return(statement, result) -> bool:
    """Should the executed statement end the body that contains it?

    True for a q:if whose branch executed a q:return, and for a q:loop that
    collected at least one. A loop that collected nothing — only q:set, or a
    filter that did not match — lets execution continue, like a false q:if.
    """
    if isinstance(result, LoopReturns):
        return len(result) > 0
    return result is not None and isinstance(statement, IfNode)


def as_return_value(result):
    """Hand a LoopReturns over as a plain list to whoever is outside the runtime."""
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
        context = exec_context.get_all_variables()

        try:
            numbers = range_numbers(node, lambda expr: self.apply_databinding(expr, context), context)

            for i in numbers:
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
        context = exec_context.get_all_variables()

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
        context = exec_context.get_all_variables()

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
        context = exec_context.get_all_variables()

        try:
            query_name = node.query_name if hasattr(node, 'query_name') else node.var_name
            query_data = context.get(query_name)

            if query_data is None:
                query_data = exec_context.get_variable(query_name)

            # LOOP-4: a query with no rows is an empty list, and the loop runs
            # zero times. `if not query_data` read it as missing, so a page with
            # a statement-level q:loop over an empty table was a 500 (found by
            # the first `quantum test` suite).
            if query_data is None:
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
        """Store in `results` what the statement returned, and only that.

        Each executed q:return becomes an item — including those of a nested
        loop, which go in flat, in order (docs/guide/loops.md, "Nested
        Loops"). A q:if whose branch returned becomes an item. The rest (rows
        of q:query, values of q:set etc.) is not a return and does not go in.

        Only LoopReturns is flattened: `<q:return value="{some_list}"/>` stays
        ONE item, even though it is a list.
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
        elif (isinstance(statement, _RENDER_ONLY_NODE_TYPES) or is_ui_node(statement)):
            # Text/HTML content is handled by HTMLRenderer._render_loop(),
            # which independently re-iterates and renders the body — it is
            # not meant to be executed here.
            return None
        else:
            # Use registry for all other statements
            return self.execute_child(statement, exec_context)

    def _parse_array_items(self, items_expr: str, context: Dict[str, Any]) -> list:
        """The list an array loop goes over (LOOP-6)."""
        return loop_list(items_expr, lambda expr: self.apply_databinding(expr, context), context)

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


def loop_list(items_expr: str, resolve, context: Dict[str, Any]) -> list:
    """LOOP-6: what `<q:loop items="…">` goes over must be a list.

    A JSON array — written in items=, or text an expression produced — is one.
    Anything else is an error, like a ui:table source (UI-5). items="{5}" used
    to loop once over "5" when it ran as a statement and draw zero rows when it
    was in markup: a mistake that looked like data, or like no data.
    """
    if not items_expr:
        return []
    got: Any = items_expr
    if '{' in items_expr and '}' in items_expr:
        got = resolve(items_expr)
    elif items_expr in context:                     # items="colors": a variable by name
        got = context[items_expr]
    if isinstance(got, list):
        return got
    if isinstance(got, str) and got.strip().startswith('['):
        try:
            parsed = json.loads(got)
        except json.JSONDecodeError as exc:
            raise ValueError(f'<q:loop items="{items_expr}"> is not a valid JSON array: {exc} (LOOP-6)') from None
        if isinstance(parsed, list):
            return parsed
    shown = repr(got) if not isinstance(got, (dict, list)) else type(got).__name__
    raise ValueError(f'<q:loop items="{items_expr}"> needs a list — an array or a q:query — '
                     f'and got {shown} ({type(got).__name__}) (LOOP-6)')


def _range_bound(attribute: str, written: Any, resolve, context: Dict[str, Any]) -> int:
    """One of from=, to=, step= of a range loop, as a whole number (LOOP-5).

    A number, a variable by name, or an expression: from="{n + 1}" is an
    expression like any other {...} attribute. It used to be read as the
    literal "{n + 1}" — an error in a statement, zero rows in markup.
    """
    if isinstance(written, int) and not isinstance(written, bool):
        return written
    text = str(written).strip() if written is not None else ''
    got: Any = text
    if '{' in text and '}' in text:
        got = resolve(text)
    elif text in context:                           # to="count": a variable by name
        got = context[text]
    if isinstance(got, float) and got.is_integer():
        got = int(got)
    if isinstance(got, str):
        try:
            got = int(got.strip())
        except ValueError:
            pass
    if isinstance(got, int) and not isinstance(got, bool):
        return got
    raise ValueError(f'<q:loop type="range" {attribute}="{text}"> needs a whole number '
                     f'and got {got!r} ({type(got).__name__}) (LOOP-5)')


def range_numbers(node: LoopNode, resolve, context: Dict[str, Any]) -> range:
    """LOOP-5: from= to to=, both included, by step= (1 by default)."""
    if node.from_value in (None, '') or node.to_value in (None, ''):
        raise ValueError('<q:loop type="range"> needs from= and to= (LOOP-5)')
    start = _range_bound('from', node.from_value, resolve, context)
    end = _range_bound('to', node.to_value, resolve, context)
    step = _range_bound('step', 1 if node.step_value in (None, '') else node.step_value, resolve, context)
    if step < 1:
        raise ValueError(f'<q:loop type="range" step="{node.step_value}"> must be 1 or more (LOOP-5)')
    return range(start, end + 1, step)
