"""
Tests for SetExecutor - q:set state management execution

Coverage target: 7% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch

from runtime.executors.control_flow.set_executor import SetExecutor
from runtime.executors.base import ExecutorError
from core.features.state_management.src.ast_node import SetNode

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime


class TestSetExecutorBasic:
    """Basic functionality tests"""

    def test_handles_set_node(self, executor):
        """Test that SetExecutor handles SetNode"""
        assert SetNode in executor.handles

    def test_handles_returns_list(self, executor):
        """Test that handles returns a list"""
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestAssignOperation:
    """Test assign operation"""

    def test_simple_string_assign(self):
        """Test simple string assignment"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("message")
        node.value = "Hello World"
        node.operation = "assign"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("message") == "Hello World"

    def test_integer_assign(self):
        """Test integer assignment"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("count")
        node.value = "42"
        node.type = "number"
        node.operation = "assign"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("count") == 42

    def test_boolean_assign_true(self):
        """Test boolean assignment (true)"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("isActive")
        node.value = "true"
        node.type = "boolean"
        node.operation = "assign"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("isActive") is True

    def test_boolean_assign_false(self):
        """Test boolean assignment (false)"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("isActive")
        node.value = "false"
        node.type = "boolean"
        node.operation = "assign"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("isActive") is False

    def test_assign_with_default_value(self):
        """Test assignment with default value when value is None"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("status")
        node.value = None
        node.default = "pending"
        node.operation = "assign"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("status") == "pending"

    def test_assign_with_databinding(self):
        """Test assignment with databinding expression"""
        runtime = MockRuntime({"firstName": "John", "lastName": "Doe"})
        executor = SetExecutor(runtime)

        node = SetNode("fullName")
        node.value = "{firstName} {lastName}"
        node.operation = "assign"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("fullName") == "John Doe"

    def test_assign_null_when_nullable(self):
        """Test assigning null when nullable is true"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("optionalField")
        node.value = None
        node.nullable = True
        node.operation = "assign"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("optionalField") is None


class TestIncrementDecrement:
    """Test increment and decrement operations"""

    def test_increment_existing_variable(self):
        """Test incrementing existing variable"""
        runtime = MockRuntime({"counter": 5})
        executor = SetExecutor(runtime)

        node = SetNode("counter")
        node.operation = "increment"
        node.step = 1

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("counter") == 6

    def test_increment_with_step(self):
        """Test increment with custom step"""
        runtime = MockRuntime({"counter": 10})
        executor = SetExecutor(runtime)

        node = SetNode("counter")
        node.operation = "increment"
        node.step = 5

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("counter") == 15

    def test_increment_new_variable(self):
        """Test increment on non-existent variable starts from step"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("newCounter")
        node.operation = "increment"
        node.step = 1

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("newCounter") == 1

    def test_decrement_existing_variable(self):
        """Test decrementing existing variable"""
        runtime = MockRuntime({"counter": 10})
        executor = SetExecutor(runtime)

        node = SetNode("counter")
        node.operation = "decrement"
        node.step = 1

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("counter") == 9

    def test_decrement_with_step(self):
        """Test decrement with custom step"""
        runtime = MockRuntime({"counter": 20})
        executor = SetExecutor(runtime)

        node = SetNode("counter")
        node.operation = "decrement"
        node.step = 3

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("counter") == 17

    def test_decrement_new_variable(self):
        """Test decrement on non-existent variable"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("newCounter")
        node.operation = "decrement"
        node.step = 1

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("newCounter") == -1

    def test_increment_with_value_expression(self):
        """Test increment with value expression"""
        runtime = MockRuntime({"base": 100})
        executor = SetExecutor(runtime)

        node = SetNode("result")
        node.operation = "increment"
        node.value = "{base}"
        node.step = 10

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("result") == 110


class TestArithmeticOperations:
    """Test add and multiply operations"""

    def test_add_to_existing_variable(self):
        """Test adding to existing variable"""
        runtime = MockRuntime({"total": 100})
        executor = SetExecutor(runtime)

        node = SetNode("total")
        node.operation = "add"
        node.value = "50"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("total") == 150

    def test_add_to_new_variable(self):
        """Test adding to non-existent variable (starts at 0)"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("newTotal")
        node.operation = "add"
        node.value = "25"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("newTotal") == 25

    def test_multiply_existing_variable(self):
        """Test multiplying existing variable"""
        runtime = MockRuntime({"value": 5})
        executor = SetExecutor(runtime)

        node = SetNode("value")
        node.operation = "multiply"
        node.value = "3"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("value") == 15

    def test_add_with_databinding(self):
        """Test add with databinding expression"""
        runtime = MockRuntime({"sum": 10, "increment": 5})
        executor = SetExecutor(runtime)

        node = SetNode("sum")
        node.operation = "add"
        node.value = "{increment}"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("sum") == 15


class TestArrayOperations:
    """Test array operations"""

    def test_append_to_array(self):
        """Test appending item to array"""
        runtime = MockRuntime({"items": ["a", "b"]})
        executor = SetExecutor(runtime)

        node = SetNode("items")
        node.operation = "append"
        node.value = "c"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("items") == ["a", "b", "c"]

    def test_prepend_to_array(self):
        """Test prepending item to array"""
        runtime = MockRuntime({"items": ["b", "c"]})
        executor = SetExecutor(runtime)

        node = SetNode("items")
        node.operation = "prepend"
        node.value = "a"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("items") == ["a", "b", "c"]

    def test_remove_from_array(self):
        """Test removing item from array"""
        runtime = MockRuntime({"items": ["a", "b", "c"]})
        executor = SetExecutor(runtime)

        node = SetNode("items")
        node.operation = "remove"
        node.value = "b"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("items") == ["a", "c"]

    def test_remove_at_index(self):
        """Test removing item at index"""
        runtime = MockRuntime({"items": ["a", "b", "c"]})
        executor = SetExecutor(runtime)

        node = SetNode("items")
        node.operation = "removeAt"
        node.index = "1"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("items") == ["a", "c"]

    def test_clear_array(self):
        """Test clearing array"""
        runtime = MockRuntime({"items": ["a", "b", "c"]})
        executor = SetExecutor(runtime)

        node = SetNode("items")
        node.operation = "clear"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("items") == []

    def test_sort_array(self):
        """Test sorting array"""
        runtime = MockRuntime({"items": ["c", "a", "b"]})
        executor = SetExecutor(runtime)

        node = SetNode("items")
        node.operation = "sort"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("items") == ["a", "b", "c"]

    def test_reverse_array(self):
        """Test reversing array"""
        runtime = MockRuntime({"items": ["a", "b", "c"]})
        executor = SetExecutor(runtime)

        node = SetNode("items")
        node.operation = "reverse"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("items") == ["c", "b", "a"]

    def test_unique_array(self):
        """Test removing duplicates from array"""
        runtime = MockRuntime({"items": ["a", "b", "a", "c", "b"]})
        executor = SetExecutor(runtime)

        node = SetNode("items")
        node.operation = "unique"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("items") == ["a", "b", "c"]

    def test_append_to_new_array(self):
        """Test appending to non-existent array creates it"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("newItems")
        node.operation = "append"
        node.value = "first"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("newItems") == ["first"]


class TestObjectOperations:
    """Test object operations"""

    def test_merge_objects(self):
        """Test merging objects"""
        runtime = MockRuntime({"config": {"a": 1}})
        executor = SetExecutor(runtime)

        node = SetNode("config")
        node.operation = "merge"
        node.value = '{"b": 2}'

        executor.execute(node, runtime.execution_context)
        result = runtime.execution_context.get_variable("config")
        assert result == {"a": 1, "b": 2}

    def test_set_property(self):
        """Test setting object property"""
        runtime = MockRuntime({"obj": {"x": 1}})
        executor = SetExecutor(runtime)

        node = SetNode("obj")
        node.operation = "setProperty"
        node.key = "y"
        node.value = "2"

        executor.execute(node, runtime.execution_context)
        result = runtime.execution_context.get_variable("obj")
        assert result == {"x": 1, "y": "2"}

    def test_delete_property(self):
        """Test deleting object property"""
        runtime = MockRuntime({"obj": {"x": 1, "y": 2}})
        executor = SetExecutor(runtime)

        node = SetNode("obj")
        node.operation = "deleteProperty"
        node.key = "x"

        executor.execute(node, runtime.execution_context)
        result = runtime.execution_context.get_variable("obj")
        assert result == {"y": 2}

    def test_clone_object(self):
        """Test cloning object from source"""
        runtime = MockRuntime({"source": {"a": 1, "b": 2}, "target": {}})
        executor = SetExecutor(runtime)

        node = SetNode("target")
        node.operation = "clone"
        node.source = "source"

        executor.execute(node, runtime.execution_context)
        result = runtime.execution_context.get_variable("target")
        assert result == {"a": 1, "b": 2}


class TestStringTransformations:
    """Test string transformation operations"""

    def test_uppercase(self):
        """Test uppercase transformation"""
        runtime = MockRuntime({"text": "hello"})
        executor = SetExecutor(runtime)

        node = SetNode("text")
        node.operation = "uppercase"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("text") == "HELLO"

    def test_lowercase(self):
        """Test lowercase transformation"""
        runtime = MockRuntime({"text": "HELLO"})
        executor = SetExecutor(runtime)

        node = SetNode("text")
        node.operation = "lowercase"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("text") == "hello"

    def test_trim(self):
        """Test trim transformation"""
        runtime = MockRuntime({"text": "  hello  "})
        executor = SetExecutor(runtime)

        node = SetNode("text")
        node.operation = "trim"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("text") == "hello"

    def test_uppercase_with_value(self):
        """Test uppercase with value expression"""
        runtime = MockRuntime({"input": "world"})
        executor = SetExecutor(runtime)

        node = SetNode("output")
        node.operation = "uppercase"
        node.value = "{input}"

        executor.execute(node, runtime.execution_context)
        assert runtime.execution_context.get_variable("output") == "WORLD"


class TestTypeConversion:
    """Test type conversion"""

    def test_convert_to_string(self):
        """Test conversion to string"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("text")
        node.value = "123"
        node.type = "string"
        node.operation = "assign"

        executor.execute(node, runtime.execution_context)
        result = runtime.execution_context.get_variable("text")
        assert result == "123"
        assert isinstance(result, str)

    def test_convert_to_integer(self):
        """Test conversion to integer"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("num")
        node.value = "42"
        node.type = "integer"
        node.operation = "assign"

        executor.execute(node, runtime.execution_context)
        result = runtime.execution_context.get_variable("num")
        assert result == 42
        assert isinstance(result, int)

    def test_convert_to_decimal(self):
        """Test conversion to decimal/float"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("price")
        node.value = "19.99"
        node.type = "decimal"
        node.operation = "assign"

        executor.execute(node, runtime.execution_context)
        result = runtime.execution_context.get_variable("price")
        assert result == 19.99
        assert isinstance(result, float)

    def test_convert_to_array(self):
        """Test conversion to array from JSON"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("items")
        node.value = "[1, 2, 3]"
        node.type = "array"
        node.operation = "assign"

        executor.execute(node, runtime.execution_context)
        result = runtime.execution_context.get_variable("items")
        assert result == [1, 2, 3]

    def test_convert_to_object(self):
        """Test conversion to object from dict variable"""
        # Note: JSON strings with curly braces get processed by databinding
        # So we test with an already-existing dict variable
        runtime = MockRuntime({"source_obj": {"key": "value"}})
        executor = SetExecutor(runtime)

        node = SetNode("config")
        node.value = "{source_obj}"  # Reference to dict variable
        node.type = "object"
        node.operation = "assign"

        executor.execute(node, runtime.execution_context)
        result = runtime.execution_context.get_variable("config")
        assert result == {"key": "value"}


class TestValidation:
    """Test validation rules"""

    def test_required_value_missing_raises_error(self):
        """Test that missing required value raises error"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("field")
        node.required = True
        node.value = ""
        node.operation = "assign"

        with pytest.raises(ExecutorError):
            executor.execute(node, runtime.execution_context)

    def test_non_nullable_null_raises_error(self):
        """Test that null on non-nullable raises error"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("field")
        node.nullable = False
        node.value = None
        node.operation = "assign"

        with pytest.raises(ExecutorError):
            executor.execute(node, runtime.execution_context)


class TestErrorHandling:
    """Test error handling"""

    def test_unsupported_operation_raises_error(self):
        """Test unsupported operation raises error"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("field")
        node.operation = "unknown_operation"
        node.value = "test"

        with pytest.raises(ExecutorError, match="Unsupported operation"):
            executor.execute(node, runtime.execution_context)

    def test_increment_non_numeric_uses_step_as_default(self):
        """Test incrementing non-numeric value falls back to step value"""
        # Note: The executor catches the error and returns step value as fallback
        runtime = MockRuntime({"text": "hello"})
        executor = SetExecutor(runtime)

        node = SetNode("text")
        node.operation = "increment"
        node.step = 5

        executor.execute(node, runtime.execution_context)
        # The exception is caught internally and step is used as the new value
        result = runtime.execution_context.get_variable("text")
        assert result == 5

    def test_array_operation_on_non_array_raises_error(self):
        """Test array operation on non-array raises error"""
        runtime = MockRuntime({"value": "string"})
        executor = SetExecutor(runtime)

        node = SetNode("value")
        node.operation = "append"
        node.value = "item"

        with pytest.raises(ExecutorError, match="non-array"):
            executor.execute(node, runtime.execution_context)

    def test_object_operation_on_non_object_raises_error(self):
        """Test object operation on non-object raises error"""
        runtime = MockRuntime({"value": "string"})
        executor = SetExecutor(runtime)

        node = SetNode("value")
        node.operation = "merge"
        node.value = '{"a": 1}'

        with pytest.raises(ExecutorError, match="non-object"):
            executor.execute(node, runtime.execution_context)

    def test_merge_invalid_json_raises_error(self):
        """Test merge with invalid JSON raises error"""
        runtime = MockRuntime({"obj": {}})
        executor = SetExecutor(runtime)

        node = SetNode("obj")
        node.operation = "merge"
        node.value = "not valid json"

        with pytest.raises(ExecutorError, match="Invalid JSON"):
            executor.execute(node, runtime.execution_context)


class TestReturnValue:
    """Test that set returns None"""

    def test_set_returns_none(self):
        """Test that set operation returns None"""
        runtime = MockRuntime()
        executor = SetExecutor(runtime)

        node = SetNode("var")
        node.value = "test"
        node.operation = "assign"

        result = executor.execute(node, runtime.execution_context)
        assert result is None
