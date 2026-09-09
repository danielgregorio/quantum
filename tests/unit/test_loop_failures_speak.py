"""
A q:loop that could not resolve its items rendered zero rows in silence.

That is indistinguishable from an empty collection, so an unresolved items=,
a typo'd query name, or a from=/to= that never resolved all looked like "no
results" on the page. The audit reported it as "q:loop swallows range errors";
the same silence covered all three loop kinds.
"""

import logging

import pytest

from quantum.core.features.loops.src.ast_node import LoopNode
from quantum.runtime.execution_context import ExecutionContext
from quantum.runtime.renderer import HTMLRenderer


@pytest.fixture
def renderer():
    return HTMLRenderer(ExecutionContext())


def _items(renderer, node, caplog):
    with caplog.at_level(logging.WARNING, logger="quantum.renderer"):
        out = renderer._get_loop_items(node)
    return out, caplog.text


class TestQueryLoop:
    def test_an_undefined_query_warns(self, renderer, caplog):
        node = LoopNode("query", "tarefas")
        node.query_name = "tarefas"
        node.items = None
        items, log = _items(renderer, node, caplog)
        assert items == []
        assert "tarefas" in log
        assert "zero rows" in log

    def test_a_non_list_query_result_warns(self, renderer, caplog):
        renderer.context.set_variable("tarefas", {"nao": "uma lista"})
        node = LoopNode("query", "tarefas")
        node.query_name = "tarefas"
        node.items = None
        items, log = _items(renderer, node, caplog)
        assert items == []
        assert "not a list" in log

    def test_a_real_query_result_is_silent(self, renderer, caplog):
        renderer.context.set_variable("tarefas", [{"id": 1}, {"id": 2}])
        node = LoopNode("query", "tarefas")
        node.query_name = "tarefas"
        node.items = None
        items, log = _items(renderer, node, caplog)
        assert len(items) == 2
        assert log == ""


class TestRangeLoop:
    def test_an_unresolved_bound_warns(self, renderer, caplog):
        node = LoopNode("range", "i")
        node.from_value = "1"
        node.to_value = "{total}"      # never resolved
        node.step_value = 1
        items, log = _items(renderer, node, caplog)
        assert items == []
        assert "zero rows" in log

    def test_a_real_range_is_silent(self, renderer, caplog):
        node = LoopNode("range", "i")
        node.from_value = "1"
        node.to_value = "3"
        node.step_value = 1
        items, log = _items(renderer, node, caplog)
        assert items == [1, 2, 3]
        assert log == ""
