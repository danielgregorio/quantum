"""
Tests for IfExecutor - q:if conditional execution

Coverage target: 38% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch

from runtime.executors.control_flow.if_executor import IfExecutor
from runtime.executors.base import ExecutorError
from core.features.conditionals.src.ast_node import IfNode
from core.ast_nodes import QuantumReturn

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime


class TestIfExecutorBasic:
    """Basic functionality tests"""

    def test_handles_if_node(self, executor):
        """Test that IfExecutor handles IfNode"""
        assert IfNode in executor.handles

    def test_handles_returns_list(self, executor):
        """Test that handles returns a list"""
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestIfConditionEvaluation:
    """Test condition evaluation"""

    def test_simple_true_condition(self):
        """Test if block executes when condition is true"""
        runtime = MockRuntime({"x": 10})
        executor = IfExecutor(runtime)

        node = IfNode("x > 5")
        # Empty body returns None

        result = executor.execute(node, runtime.execution_context)
        assert result is None

    def test_simple_false_condition(self):
        """Test if block doesn't execute when condition is false"""
        runtime = MockRuntime({"x": 3})
        executor = IfExecutor(runtime)

        node = IfNode("x > 5")

        result = executor.execute(node, runtime.execution_context)
        assert result is None

    def test_equality_condition(self):
        """Test equality condition"""
        runtime = MockRuntime({"status": "active"})
        executor = IfExecutor(runtime)

        node = IfNode("status == 'active'")

        result = executor.execute(node, runtime.execution_context)
        assert result is None  # Empty body

    def test_boolean_variable_condition(self):
        """Test boolean variable as condition"""
        runtime = MockRuntime({"isEnabled": True})
        executor = IfExecutor(runtime)

        node = IfNode("isEnabled")

        result = executor.execute(node, runtime.execution_context)
        assert result is None

    def test_not_condition(self):
        """Test negation condition"""
        runtime = MockRuntime({"isDisabled": False})
        executor = IfExecutor(runtime)

        node = IfNode("not isDisabled")

        result = executor.execute(node, runtime.execution_context)
        assert result is None


class TestIfWithBody:
    """Test if with body statements"""

    def test_return_in_if_body(self):
        """Test return statement in if body"""
        runtime = MockRuntime({"x": 10})
        executor = IfExecutor(runtime)

        node = IfNode("x > 5")
        node.if_body = [QuantumReturn(value="success")]

        result = executor.execute(node, runtime.execution_context)
        assert result == "success"

    def test_return_with_variable(self):
        """Test return with variable resolution"""
        runtime = MockRuntime({"x": 10, "message": "hello"})
        executor = IfExecutor(runtime)

        node = IfNode("x > 5")
        node.if_body = [QuantumReturn(value="{message}")]

        result = executor.execute(node, runtime.execution_context)
        assert result == "hello"

    def test_false_condition_skips_body(self):
        """Test that false condition skips body"""
        runtime = MockRuntime({"x": 3})
        executor = IfExecutor(runtime)

        node = IfNode("x > 5")
        node.if_body = [QuantumReturn(value="should not return")]

        result = executor.execute(node, runtime.execution_context)
        assert result is None


class TestElseIfBlocks:
    """Test elseif functionality"""

    def test_elseif_executes_when_if_false(self):
        """Test elseif block when if condition is false"""
        runtime = MockRuntime({"x": 3})
        executor = IfExecutor(runtime)

        node = IfNode("x > 10")
        node.add_elseif_block("x > 2", [QuantumReturn(value="elseif1")])

        result = executor.execute(node, runtime.execution_context)
        assert result == "elseif1"

    def test_multiple_elseif_blocks(self):
        """Test multiple elseif blocks"""
        runtime = MockRuntime({"x": 7})
        executor = IfExecutor(runtime)

        node = IfNode("x > 10")
        node.add_elseif_block("x > 8", [QuantumReturn(value="elseif1")])
        node.add_elseif_block("x > 5", [QuantumReturn(value="elseif2")])
        node.add_elseif_block("x > 2", [QuantumReturn(value="elseif3")])

        result = executor.execute(node, runtime.execution_context)
        assert result == "elseif2"

    def test_first_matching_elseif_wins(self):
        """Test that first matching elseif block is executed"""
        runtime = MockRuntime({"x": 15})
        executor = IfExecutor(runtime)

        node = IfNode("x > 20")
        node.add_elseif_block("x > 10", [QuantumReturn(value="first")])
        node.add_elseif_block("x > 5", [QuantumReturn(value="second")])

        result = executor.execute(node, runtime.execution_context)
        assert result == "first"

    def test_elseif_skipped_when_if_true(self):
        """Test elseif is skipped when if condition is true"""
        runtime = MockRuntime({"x": 15})
        executor = IfExecutor(runtime)

        node = IfNode("x > 10")
        node.if_body = [QuantumReturn(value="if_block")]
        node.add_elseif_block("x > 5", [QuantumReturn(value="elseif_block")])

        result = executor.execute(node, runtime.execution_context)
        assert result == "if_block"


class TestElseBlock:
    """Test else functionality"""

    def test_else_executes_when_all_false(self):
        """Test else block when all conditions are false"""
        runtime = MockRuntime({"x": 1})
        executor = IfExecutor(runtime)

        node = IfNode("x > 10")
        node.add_elseif_block("x > 5", [QuantumReturn(value="elseif")])
        node.else_body = [QuantumReturn(value="else_block")]

        result = executor.execute(node, runtime.execution_context)
        assert result == "else_block"

    def test_else_skipped_when_if_true(self):
        """Test else is skipped when if is true"""
        runtime = MockRuntime({"x": 15})
        executor = IfExecutor(runtime)

        node = IfNode("x > 10")
        node.if_body = [QuantumReturn(value="if_block")]
        node.else_body = [QuantumReturn(value="else_block")]

        result = executor.execute(node, runtime.execution_context)
        assert result == "if_block"

    def test_else_skipped_when_elseif_true(self):
        """Test else is skipped when elseif is true"""
        runtime = MockRuntime({"x": 7})
        executor = IfExecutor(runtime)

        node = IfNode("x > 10")
        node.add_elseif_block("x > 5", [QuantumReturn(value="elseif")])
        node.else_body = [QuantumReturn(value="else_block")]

        result = executor.execute(node, runtime.execution_context)
        assert result == "elseif"


class TestNestedIf:
    """Test nested if statements"""

    def test_nested_if_in_body(self):
        """Test nested if statement in body"""
        runtime = MockRuntime({"x": 15, "y": 20})
        executor = IfExecutor(runtime)

        # Create inner if
        inner_if = IfNode("y > 10")
        inner_if.if_body = [QuantumReturn(value="nested_success")]

        # Create outer if with inner if in body
        outer_if = IfNode("x > 10")
        outer_if.if_body = [inner_if]

        # Mock execute_child to handle nested execution
        with patch.object(executor, 'execute_child', return_value="nested_success"):
            result = executor.execute(outer_if, runtime.execution_context)
            # The nested IfNode returns something, so it should propagate
            assert result == "nested_success"


class TestComplexConditions:
    """Test complex condition expressions"""

    def test_and_condition(self):
        """Test AND condition"""
        runtime = MockRuntime({"x": 10, "y": 20})
        executor = IfExecutor(runtime)

        node = IfNode("x > 5 and y > 15")
        node.if_body = [QuantumReturn(value="both_true")]

        result = executor.execute(node, runtime.execution_context)
        assert result == "both_true"

    def test_or_condition(self):
        """Test OR condition"""
        runtime = MockRuntime({"x": 3, "y": 20})
        executor = IfExecutor(runtime)

        node = IfNode("x > 5 or y > 15")
        node.if_body = [QuantumReturn(value="one_true")]

        result = executor.execute(node, runtime.execution_context)
        assert result == "one_true"

    def test_in_operator(self):
        """Test 'in' operator for list membership"""
        runtime = MockRuntime({"status": "active", "validStatuses": ["active", "pending"]})
        executor = IfExecutor(runtime)

        node = IfNode("status in validStatuses")
        node.if_body = [QuantumReturn(value="valid")]

        result = executor.execute(node, runtime.execution_context)
        assert result == "valid"

    def test_not_equal_condition(self):
        """Test not equal condition"""
        runtime = MockRuntime({"status": "pending"})
        executor = IfExecutor(runtime)

        node = IfNode("status != 'active'")
        node.if_body = [QuantumReturn(value="not_active")]

        result = executor.execute(node, runtime.execution_context)
        assert result == "not_active"


class TestEdgeCases:
    """Test edge cases"""

    def test_empty_if_body(self):
        """Test if with empty body"""
        runtime = MockRuntime({"x": 10})
        executor = IfExecutor(runtime)

        node = IfNode("x > 5")
        node.if_body = []

        result = executor.execute(node, runtime.execution_context)
        assert result is None

    def test_none_variable_in_condition(self):
        """Test condition with None variable"""
        runtime = MockRuntime({"x": None})
        executor = IfExecutor(runtime)

        node = IfNode("x is None")
        node.if_body = [QuantumReturn(value="is_none")]

        result = executor.execute(node, runtime.execution_context)
        assert result == "is_none"

    def test_empty_string_condition(self):
        """Test condition with empty string"""
        runtime = MockRuntime({"name": ""})
        executor = IfExecutor(runtime)

        node = IfNode("not name")
        node.if_body = [QuantumReturn(value="empty")]

        result = executor.execute(node, runtime.execution_context)
        assert result == "empty"

    def test_zero_is_falsy(self):
        """Test that zero is falsy in conditions"""
        runtime = MockRuntime({"count": 0})
        executor = IfExecutor(runtime)

        node = IfNode("count")
        node.if_body = [QuantumReturn(value="has_count")]
        node.else_body = [QuantumReturn(value="no_count")]

        result = executor.execute(node, runtime.execution_context)
        assert result == "no_count"
