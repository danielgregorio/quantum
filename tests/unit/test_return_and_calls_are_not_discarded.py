r"""
Two ways the runtime silently dropped the author's code.

1. `<q:return>` inside `<q:if>` / `<q:else>` / `<q:loop>` was DROPPED by the
   parser. There is no parser registered for 'return' — the component level
   collects the returns separately, with _find_all_elements — so a nested
   return fell into the dispatcher's `return None` and vanished. The component
   went on and returned the next return, or nothing.

   `<q:if condition="n > 3"><q:return value="BIGGER"/></q:if>` did not return
   BIGGER. No error, no log.

2. An expression that STARTED with a q:function call had the rest dropped. The
   shortcut matched `^\s*(\w+)\s*\(` and sent it to _evaluate_function_call,
   whose regex `(\w+)\((.*)\)` takes up to the last parenthesis and ignores
   what comes after.

   `{double(a) * 10}` returned 10 instead of 100 — and `{10 * double(a)}` gave
   100, because it did not start with the call. The SAME sum with different
   results depending on the order of the factors.
"""

import pathlib
import tempfile

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime


def run_body(body):
    path = pathlib.Path(tempfile.mkdtemp()) / 'c.q'
    path.write_text(f'<q:component name="C">{body}</q:component>',
                    encoding='utf-8')
    node = QuantumParser().parse_file(str(path))
    return ComponentRuntime().execute_component(node, {})


class TestNestedReturn:
    def test_inside_a_true_if(self):
        assert run_body(
            '<q:set name="n" value="5" type="number"/>'
            '<q:if condition="n > 3"><q:return value="BIGGER"/></q:if>'
            '<q:return value="fallback"/>') == 'BIGGER'

    def test_a_false_if_goes_on_to_the_next(self):
        assert run_body(
            '<q:set name="n" value="1" type="number"/>'
            '<q:if condition="n > 3"><q:return value="BIGGER"/></q:if>'
            '<q:return value="fallback"/>') == 'fallback'

    def test_inside_an_else(self):
        assert run_body(
            '<q:set name="n" value="1" type="number"/>'
            '<q:if condition="n > 3"><q:return value="BIGGER"/>'
            '<q:else><q:return value="SMALLER"/></q:else></q:if>') == 'SMALLER'

    def test_the_top_level_return_still_works(self):
        assert run_body('<q:return value="TOP"/>') == 'TOP'

    def test_the_parser_no_longer_drops_the_node(self):
        path = pathlib.Path(tempfile.mkdtemp()) / 'c.q'
        path.write_text(
            '<q:component name="C"><q:if condition="1 == 1">'
            '<q:return value="X"/></q:if></q:component>', encoding='utf-8')
        node = QuantumParser().parse_file(str(path))
        body = node.statements[0].if_body
        assert any(type(n).__name__ == 'QuantumReturn' for n in body), (
            f'the q:return vanished from if_body: {[type(n).__name__ for n in body]}')


class TestReturnInsideALoop:
    """`<q:return>` inside `<q:loop>` was evaluated and THROWN AWAY.

    The LoopExecutor even collected the values, but the component (and the
    function, and the q:if around it) only treated q:if as a return — the
    loop's result was ignored and the component returned None. The repo's 7
    examples with this pattern gave "Component executed without return", and
    getting-started.md documented output no version of the code produced.

    The rule is now the same as q:if's: a loop that executed at least one
    q:return ends the body with the list of values; a loop that executed none
    lets execution go on.
    """

    def test_the_getting_started_example(self):
        # docs/guide/getting-started.md, "Adding Dynamic Content", verbatim.
        assert run_body(
            '<q:set name="greeting" value="Hello" />'
            '<q:loop type="list" var="name" items="Alice,Bob,Charlie">'
            '<q:return value="{greeting} {name}!" />'
            '</q:loop>') == ['Hello Alice!', 'Hello Bob!', 'Hello Charlie!']

    def test_an_if_inside_the_loop_filters(self):
        assert run_body(
            '<q:loop type="range" var="i" from="1" to="5">'
            '<q:if condition="i % 2 == 0"><q:return value="even {i}"/></q:if>'
            '</q:loop>') == ['even 2', 'even 4']

    def test_a_loop_without_a_return_goes_on_to_the_next(self):
        assert run_body(
            '<q:set name="t" value="0" type="number"/>'
            '<q:loop type="range" var="i" from="1" to="3">'
            '<q:set name="t" operation="add" value="{i}"/></q:loop>'
            '<q:return value="Total {t}"/>') == 'Total 6'

    def test_a_filter_that_does_not_match_goes_on_to_the_next(self):
        assert run_body(
            '<q:loop type="range" var="i" from="1" to="3">'
            '<q:if condition="i > 10"><q:return value="{i}"/></q:if>'
            '</q:loop><q:return value="none"/>') == 'none'

    def test_a_loop_inside_an_if_ends_the_if(self):
        assert run_body(
            '<q:set name="n" value="5" type="number"/>'
            '<q:if condition="n > 3">'
            '<q:loop type="range" var="i" from="1" to="2">'
            '<q:return value="x{i}"/></q:loop></q:if>'
            '<q:return value="fallback"/>') == ['x1', 'x2']

    def test_a_nested_loop_flattens_as_the_guide_documents(self):
        # docs/guide/loops.md, "Nested Loops": ["(1,1)", "(1,2)", "(2,1)", "(2,2)"]
        assert run_body(
            '<q:loop type="range" var="x" from="1" to="2">'
            '<q:loop type="range" var="y" from="1" to="2">'
            '<q:return value="({x},{y})"/></q:loop></q:loop>'
        ) == ['(1,1)', '(1,2)', '(2,1)', '(2,2)']

    def test_a_list_return_is_still_one_item(self):
        # Only a loop's result is flattened; a value that happens to be a list
        # goes in whole.
        result = run_body(
            '''<q:set name="pair" value='["a", "b"]' type="array"/>'''
            '<q:loop type="range" var="i" from="1" to="2">'
            '<q:if condition="i > 0"><q:return value="{pair}"/></q:if>'
            '</q:loop>')
        assert result == [['a', 'b'], ['a', 'b']]

    def test_a_function_returns_the_loop_s_list(self):
        assert str(run_body(
            '<q:function name="evens">'
            '<q:loop type="range" var="i" from="1" to="6">'
            '<q:if condition="i % 2 == 0"><q:return value="{i}"/></q:if>'
            '</q:loop></q:function>'
            '<q:return value="{len(evens())}"/>')) == '3'

    def test_the_result_is_a_plain_list(self):
        # LoopReturns is an internal marker; it must not leak to the caller.
        result = run_body(
            '<q:loop type="range" var="i" from="1" to="2">'
            '<q:return value="{i}"/></q:loop>')
        assert type(result) is list

    def test_the_value_of_a_statement_that_is_not_a_return_does_not_count(self):
        # A q:query inside the loop returns rows; that is not a return and must
        # not make the loop "return" the rows.
        from quantum.core.features.state_management.src.ast_node import SetNode
        from quantum.runtime.executors.control_flow.loop_executor import (
            LoopExecutor, LoopReturns)
        collected = LoopReturns()
        LoopExecutor._collect(collected, SetNode('x'), [{'row': 1}])
        assert collected == []


# The outputs of docs/guide/loops.md (which were made up) are checked by
# tests/docs/test_guide_examples_run.py, together with the other pages'.


class TestAFunctionCallInAnExpression:
    FUNCTION = ('<q:function name="double"><q:param name="x" type="number"/>'
                '<q:return value="{x * 2}"/></q:function>'
                '<q:set name="a" value="5" type="number"/>')

    @pytest.mark.parametrize("expression,expected", [
        ('{double(a)}', '10'),
        ('{double(a) * 10}', '100'),
        ('{10 * double(a)}', '100'),
        ('{double(a) + double(a)}', '20'),
        ('{double(a) - 1}', '9'),
    ])
    def test_the_whole_expression_is_evaluated(self, expression, expected):
        result = run_body(
            self.FUNCTION + f'<q:set name="r" value="{expression}"/>'
            '<q:return value="{r}"/>')
        assert str(result) == expected

    def test_the_order_of_the_factors_does_not_change_the_result(self):
        # The symptom that gave it away: `double(a) * 10` gave 10 and
        # `10 * double(a)` gave 100.
        one = run_body(self.FUNCTION + '<q:return value="{double(a) * 10}"/>')
        other = run_body(self.FUNCTION + '<q:return value="{10 * double(a)}"/>')
        assert str(one) == str(other) == '100'
