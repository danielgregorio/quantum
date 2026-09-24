"""Conformance: SPEC.md sections 1 (Return) and 2 (Loops)."""

import pytest


class TestReturn:
    def test_the_first_return_in_document_order_wins(self, run_body):
        # RET-1 (was gap G1: the top-level return was deferred and a later q:if won)
        assert run_body(
            '<q:return value="A"/><q:set name="n" value="1"/>'
            '<q:if condition="n == 1"><q:return value="B"/></q:if>') == 'A'

    def test_a_top_level_return_after_statements(self, run_body):
        # RET-1
        assert run_body('<q:set name="x" value="ok"/><q:return value="{x}"/>'
                        '<q:return value="never"/>') == 'ok'

    def test_a_single_expression_keeps_its_type(self, run_body):
        # RET-2
        assert run_body('<q:set name="i" value="7" type="number"/>'
                        '<q:return value="{i}"/>') == 7

    def test_interpolation_with_text_is_text(self, run_body):
        # RET-2 (was G2: "{i}.{j}" became the number 1.2)
        assert run_body('<q:set name="i" value="1"/><q:set name="j" value="2"/>'
                        '<q:return value="{i}.{j}"/>') == '1.2'

    def test_a_literal_is_not_converted(self, run_body):
        # RET-2 (was G2b: "007" became 7)
        assert run_body('<q:return value="007"/>') == '007'
        assert run_body('<q:return value="01310-000"/>') == '01310-000'

    def test_a_return_inside_an_if_ends(self, run_body):
        # RET-3
        assert run_body('<q:set name="n" value="5" type="number"/>'
                        '<q:if condition="n > 3"><q:return value="BIGGER"/></q:if>'
                        '<q:return value="fallback"/>') == 'BIGGER'

    def test_an_if_without_a_return_executed_goes_on(self, run_body):
        # RET-3
        assert run_body('<q:set name="n" value="1" type="number"/>'
                        '<q:if condition="n > 3"><q:return value="BIGGER"/></q:if>'
                        '<q:return value="fallback"/>') == 'fallback'


class TestLoops:
    def test_each_return_becomes_an_item(self, run_body):
        # LOOP-1
        assert run_body('<q:loop type="range" var="i" from="1" to="3">'
                        '<q:return value="n{i}"/></q:loop>') == ['n1', 'n2', 'n3']

    def test_a_loop_with_a_return_ends_the_body(self, run_body):
        # LOOP-2
        assert run_body('<q:loop type="range" var="i" from="1" to="2">'
                        '<q:return value="{i}"/></q:loop><q:return value="after"/>') == [1, 2]

    def test_a_loop_without_a_return_lets_it_go_on(self, run_body):
        # LOOP-2
        assert run_body('<q:loop type="range" var="i" from="1" to="3">'
                        '<q:if condition="i > 10"><q:return value="{i}"/></q:if>'
                        '</q:loop><q:return value="none"/>') == 'none'

    def test_a_nested_loop_flattens(self, run_body):
        # LOOP-3
        assert run_body('<q:loop type="range" var="x" from="1" to="2">'
                        '<q:loop type="range" var="y" from="1" to="2">'
                        '<q:return value="({x},{y})"/></q:loop></q:loop>'
                        ) == ['(1,1)', '(1,2)', '(2,1)', '(2,2)']

    def test_a_list_value_goes_in_as_one_item(self, run_body):
        # LOOP-3
        assert run_body('''<q:set name="pair" value='["a", "b"]' type="array"/>'''
                        '<q:loop type="range" var="i" from="1" to="2">'
                        '<q:if condition="i > 0"><q:return value="{pair}"/></q:if>'
                        '</q:loop>') == [['a', 'b'], ['a', 'b']]

    def test_a_query_with_no_rows_loops_zero_times(self, run_body):
        # LOOP-4 (a statement-level loop over an empty query was a 500: the
        # empty list was read as "not found"; found by the first quantum test suite)
        assert run_body('''<q:set name="rows" value='[]' type="array"/>'''
                        '<q:loop query="rows"><q:return value="row"/></q:loop>'
                        '<q:return value="after"/>') == 'after'

    def test_a_query_loop_over_a_name_that_does_not_exist_is_an_error(self, run_body):
        # LOOP-4
        import pytest
        with pytest.raises(Exception, match="nothing"):
            run_body('<q:loop query="nothing"><q:return value="row"/></q:loop>')


# ------------------------------------------------------------------ LOOP-5: the loop types

def collect(loop):
    return ('<q:set name="r" value="[]" type="array"/>' + loop.replace('BODY', '<q:set name="r" operation="append" value="ITEM"/>')
            + '<q:return value="{r}"/>')


@pytest.mark.parametrize('loop,item,expected', [
    ('<q:loop type="range" var="i" from="1" to="10" step="3">BODY</q:loop>', '{i}', [1, 4, 7, 10]),
    ('<q:loop type="range" var="i" from="1" to="3">BODY</q:loop>', '{i}', [1, 2, 3]),
    ('<q:loop type="range" var="i" from="3" to="1">BODY</q:loop>', '{i}', []),
    ('<q:loop type="array" var="x" index="k" items=\'["a", "b"]\'>BODY</q:loop>', '{k}{x}', ['0a', '1b']),
    ('<q:loop type="list" var="x" items="a|b| c" delimiter="|">BODY</q:loop>', '[{x}]', ['[a]', '[b]', '[c]']),
    ('<q:loop type="list" var="x" items="a, b">BODY</q:loop>', '[{x}]', ['[a]', '[b]']),
    ('<q:loop var="x" items=\'["a"]\'>BODY</q:loop>', '{x}', ['a']),
    ('<q:loop var="i" from="1" to="2">BODY</q:loop>', '{i}', [1, 2]),
])
def test_the_loop_types(run_body, loop, item, expected):
    # LOOP-5
    assert run_body(collect(loop).replace('ITEM', item)) == expected


def test_another_loop_type_is_an_error(run_body):
    # LOOP-5, PARSE-5: a parse error now, with the line
    with pytest.raises(Exception, match='type="galaxy"> does not exist'):
        run_body('<q:loop type="galaxy" var="x" items="a"><q:set name="y" value="1"/></q:loop>')


@pytest.mark.parametrize('items,got', [('{5}', '5 (int)'), ("{'text'}", "'text' (str)"),
                                       ('{d}', 'dict (dict)'), ('{nothing_here}', None)])
def test_a_loop_over_something_that_is_not_a_list_is_an_error(run_body, items, got):
    # LOOP-6 (items="{5}" looped once over "5"; in markup it drew zero rows)
    with pytest.raises(Exception) as error:
        run_body('<q:set name="nothing_here" value=""/>'
                 '''<q:set name="d" value='{"a": 1}' type="object"/>'''
                 f'<q:loop var="x" items="{items}"><q:return value="{{x}}"/></q:loop>')
    assert 'needs a list' in str(error.value) and 'LOOP-6' in str(error.value)
    if got:
        assert got in str(error.value)


def test_a_loop_in_markup_over_something_that_is_not_a_list_is_an_error(serve_pages):
    # LOOP-6: it used to render zero rows with a warning — the same as an empty list
    client = serve_pages(p='<q:component name="p" xmlns:q="https://quantum.lang/ns"><ul>'
                           '<q:loop var="x" items="{5}"><li>{x}</li></q:loop></ul></q:component>')
    assert client.get('/p').status_code == 500


def test_json_array_text_is_a_list(run_body):
    # LOOP-6
    assert run_body('''<q:loop var="x" items='["a", "b"]'><q:return value="{x}"/></q:loop>''') == ['a', 'b']
