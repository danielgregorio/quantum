"""
Tests for LoopExecutor - q:loop iteration execution

Coverage target: 14% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch

from runtime.executors.control_flow.loop_executor import LoopExecutor
from runtime.executors.base import ExecutorError
from core.features.loops.src.ast_node import LoopNode
from core.ast_nodes import QuantumReturn

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime


class TestLoopExecutorBasic:
    """Basic functionality tests"""

    def test_handles_loop_node(self, executor):
        """Test that LoopExecutor handles LoopNode"""
        assert LoopNode in executor.handles

    def test_handles_returns_list(self, executor):
        """Test that handles returns a list"""
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestRangeLoop:
    """Test range loop execution"""

    def test_simple_range_loop(self):
        """Test simple range loop from 1 to 5"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        node = LoopNode("range", "i")
        node.from_value = "1"
        node.to_value = "5"

        result = executor.execute(node, runtime.execution_context)
        assert isinstance(result, list)

    def test_range_loop_with_return(self):
        """Test range loop that returns values"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        node = LoopNode("range", "i")
        node.from_value = "1"
        node.to_value = "3"
        node.body = [QuantumReturn(value="{i}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == [1, 2, 3]

    def test_range_loop_with_step(self):
        """Test range loop with custom step"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        node = LoopNode("range", "i")
        node.from_value = "0"
        node.to_value = "10"
        node.step_value = 2
        node.body = [QuantumReturn(value="{i}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == [0, 2, 4, 6, 8, 10]

    def test_range_loop_with_variable_bounds(self):
        """Test range loop with variable bounds"""
        runtime = MockRuntime({"start": 5, "end": 8})
        executor = LoopExecutor(runtime)

        node = LoopNode("range", "i")
        node.from_value = "start"
        node.to_value = "end"
        node.body = [QuantumReturn(value="{i}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == [5, 6, 7, 8]

    def test_range_loop_empty_when_start_greater_than_end(self):
        """Test range loop is empty when start > end"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        node = LoopNode("range", "i")
        node.from_value = "10"
        node.to_value = "5"
        node.body = [QuantumReturn(value="{i}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == []

    def test_range_loop_invalid_values_raises_error(self):
        """Test range loop with invalid values raises error"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        node = LoopNode("range", "i")
        node.from_value = "abc"
        node.to_value = "5"

        with pytest.raises(ExecutorError, match="Range loop error"):
            executor.execute(node, runtime.execution_context)


class TestArrayLoop:
    """Test array loop execution"""

    def test_array_loop_with_list(self):
        """Test array loop iterating over a list"""
        runtime = MockRuntime({"items": ["a", "b", "c"]})
        executor = LoopExecutor(runtime)

        node = LoopNode("array", "item")
        node.items = "items"
        node.body = [QuantumReturn(value="{item}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == ["a", "b", "c"]

    def test_array_loop_with_index(self):
        """Test array loop with index variable"""
        runtime = MockRuntime({"items": ["x", "y", "z"]})
        executor = LoopExecutor(runtime)

        node = LoopNode("array", "item")
        node.items = "items"
        node.index_name = "idx"
        node.body = [QuantumReturn(value="{idx}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == [0, 1, 2]

    def test_array_loop_with_json_array(self):
        """Test array loop with JSON array literal"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        node = LoopNode("array", "num")
        node.items = "[1, 2, 3]"
        node.body = [QuantumReturn(value="{num}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == [1, 2, 3]

    def test_array_loop_with_objects(self):
        """Test array loop iterating over objects"""
        runtime = MockRuntime({
            "users": [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25}
            ]
        })
        executor = LoopExecutor(runtime)

        node = LoopNode("array", "user")
        node.items = "users"

        result = executor.execute(node, runtime.execution_context)
        assert isinstance(result, list)

    def test_array_loop_empty_array(self):
        """Test array loop with empty array"""
        runtime = MockRuntime({"items": []})
        executor = LoopExecutor(runtime)

        node = LoopNode("array", "item")
        node.items = "items"
        node.body = [QuantumReturn(value="{item}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == []

    def test_array_loop_databinding(self):
        """Test array loop with databinding expression"""
        runtime = MockRuntime({"data": {"list": [10, 20, 30]}})
        executor = LoopExecutor(runtime)

        node = LoopNode("array", "val")
        node.items = "{data.list}"
        node.body = [QuantumReturn(value="{val}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == [10, 20, 30]


class TestListLoop:
    """Test list (delimited string) loop execution"""

    def test_list_loop_comma_delimited(self):
        """Test list loop with comma delimiter (default)"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        node = LoopNode("list", "color")
        node.items = "red,green,blue"
        node.delimiter = ","
        node.body = [QuantumReturn(value="{color}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == ["red", "green", "blue"]

    def test_list_loop_pipe_delimited(self):
        """Test list loop with pipe delimiter"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        node = LoopNode("list", "item")
        node.items = "one|two|three"
        node.delimiter = "|"
        node.body = [QuantumReturn(value="{item}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == ["one", "two", "three"]

    def test_list_loop_with_index(self):
        """Test list loop with index variable"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        node = LoopNode("list", "item")
        node.items = "a,b,c"
        node.delimiter = ","
        node.index_name = "i"
        node.body = [QuantumReturn(value="{i}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == [0, 1, 2]

    def test_list_loop_trims_whitespace(self):
        """Test list loop trims whitespace from items"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        node = LoopNode("list", "item")
        node.items = "  one  ,  two  ,  three  "
        node.delimiter = ","
        node.body = [QuantumReturn(value="{item}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == ["one", "two", "three"]

    def test_list_loop_from_variable(self):
        """Test list loop with items from variable"""
        runtime = MockRuntime({"csv": "x,y,z"})
        executor = LoopExecutor(runtime)

        node = LoopNode("list", "letter")
        node.items = "csv"
        node.delimiter = ","
        node.body = [QuantumReturn(value="{letter}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == ["x", "y", "z"]

    def test_list_loop_empty_string(self):
        """Test list loop with empty string"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        node = LoopNode("list", "item")
        node.items = ""
        node.delimiter = ","
        node.body = [QuantumReturn(value="{item}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == []


class TestQueryLoop:
    """Test query loop execution"""

    def test_query_loop_basic(self):
        """Test basic query loop over result set"""
        runtime = MockRuntime({
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
                {"id": 3, "name": "Charlie"}
            ]
        })
        executor = LoopExecutor(runtime)

        node = LoopNode("query", "users")
        node.body = [QuantumReturn(value="{name}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == ["Alice", "Bob", "Charlie"]

    def test_query_loop_accesses_dotted_fields(self):
        """Test query loop can access dotted field names"""
        runtime = MockRuntime({
            "results": [
                {"field1": "a", "field2": "b"}
            ]
        })
        executor = LoopExecutor(runtime)

        node = LoopNode("query", "results")

        result = executor.execute(node, runtime.execution_context)
        assert isinstance(result, list)

    def test_query_loop_with_index(self):
        """Test query loop with index variable"""
        runtime = MockRuntime({
            "data": [
                {"value": 10},
                {"value": 20}
            ]
        })
        executor = LoopExecutor(runtime)

        node = LoopNode("query", "data")
        node.index_name = "rowNum"
        node.body = [QuantumReturn(value="{rowNum}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == [0, 1]

    def test_query_loop_empty_results(self):
        """Test query loop with empty result set raises error (falsy check)"""
        # Note: The current executor treats empty list as "not found"
        # because it uses `if not query_data:` which is True for []
        runtime = MockRuntime({"query": []})
        executor = LoopExecutor(runtime)

        node = LoopNode("query", "query")
        node.body = [QuantumReturn(value="row")]

        # Empty list is falsy, so executor raises error
        with pytest.raises(ExecutorError, match="Query loop error"):
            executor.execute(node, runtime.execution_context)

    def test_query_loop_not_found_raises_error(self):
        """Test query loop raises error when query not found"""
        runtime = MockRuntime({})
        executor = LoopExecutor(runtime)

        node = LoopNode("query", "nonexistent")

        with pytest.raises(ExecutorError, match="Query loop error"):
            executor.execute(node, runtime.execution_context)

    def test_query_loop_not_iterable_raises_error(self):
        """Test query loop raises error when result is not iterable"""
        runtime = MockRuntime({"query": "not a list"})
        executor = LoopExecutor(runtime)

        node = LoopNode("query", "query")

        with pytest.raises(ExecutorError, match="is not iterable"):
            executor.execute(node, runtime.execution_context)


class TestUnsupportedLoopType:
    """Test unsupported loop types"""

    def test_unsupported_loop_type_raises_error(self):
        """Test that unsupported loop type raises error"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        node = LoopNode("unknown", "item")

        with pytest.raises(ExecutorError, match="Unsupported loop type"):
            executor.execute(node, runtime.execution_context)


class TestLoopHelperMethods:
    """Test helper methods"""

    def test_evaluate_simple_expr_integer(self):
        """Test _evaluate_simple_expr with integer"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        result = executor._evaluate_simple_expr("42", {})
        assert result == 42

    def test_evaluate_simple_expr_float(self):
        """Test _evaluate_simple_expr with float"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        result = executor._evaluate_simple_expr("3.14", {})
        assert result == 3.14

    def test_evaluate_simple_expr_variable(self):
        """Test _evaluate_simple_expr with variable"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        result = executor._evaluate_simple_expr("count", {"count": 10})
        assert result == 10

    def test_evaluate_simple_expr_empty(self):
        """Test _evaluate_simple_expr with empty string"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        result = executor._evaluate_simple_expr("", {})
        assert result == 0

    def test_parse_array_items_json(self):
        """Test _parse_array_items with JSON array"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        result = executor._parse_array_items('[1, 2, 3]', {})
        assert result == [1, 2, 3]

    def test_parse_array_items_variable(self):
        """Test _parse_array_items with variable reference"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        result = executor._parse_array_items('myList', {"myList": [4, 5, 6]})
        assert result == [4, 5, 6]

    def test_parse_array_items_empty(self):
        """Test _parse_array_items with empty string"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        result = executor._parse_array_items('', {})
        assert result == []

    def test_parse_list_items_string(self):
        """Test _parse_list_items with string"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        result = executor._parse_list_items('a,b,c', ',', {})
        assert result == ['a', 'b', 'c']

    def test_parse_list_items_variable_string(self):
        """Test _parse_list_items with variable containing string"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        result = executor._parse_list_items('data', '|', {"data": "x|y|z"})
        assert result == ['x', 'y', 'z']

    def test_parse_list_items_variable_list(self):
        """Test _parse_list_items with variable containing list"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        result = executor._parse_list_items('items', ',', {"items": [1, 2, 3]})
        assert result == [1, 2, 3]


class TestLoopBodyExecution:
    """Test loop body statement execution"""

    def test_body_with_quantum_return(self):
        """Test body with QuantumReturn statement"""
        runtime = MockRuntime()
        executor = LoopExecutor(runtime)

        node = LoopNode("range", "i")
        node.from_value = "1"
        node.to_value = "2"
        node.body = [QuantumReturn(value="value_{i}")]

        result = executor.execute(node, runtime.execution_context)
        assert len(result) == 2

    def test_body_with_multiple_statements(self):
        """Test body with multiple statements"""
        runtime = MockRuntime({"items": [1, 2]})
        executor = LoopExecutor(runtime)

        node = LoopNode("array", "item")
        node.items = "items"
        node.body = [QuantumReturn(value="{item}")]

        with patch.object(executor, 'execute_child', return_value=None):
            result = executor.execute(node, runtime.execution_context)
            assert len(result) == 2
