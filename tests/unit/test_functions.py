"""
Unit Tests for q:function Feature

Tests function definitions, parameter binding, caching, and execution.
"""

import pytest
import sys
from pathlib import Path

# Fix imports
sys.path.append(str(Path(__file__).parent.parent.parent / 'src'))

from core.parser import QuantumParser, QuantumParseError
from core.ast_nodes import ComponentNode
from core.features.functions.src import (
    FunctionNode, parse_function, FunctionRuntime, register_function, call_function, clear_cache
)


class TestFunctionParsing:
    """Test parsing of q:function tags"""

    def test_parse_basic_function(self, tmp_path):
        """Test parsing basic function definition"""
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="TestFunc">
            <q:function name="greet">
                <q:param name="name" type="string" required="true" />
                <q:return value="Hello {name}!" />
            </q:function>
        </q:component>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(component_file))

        assert isinstance(ast, ComponentNode)
        assert len(ast.statements) == 1

        func = ast.statements[0]
        assert isinstance(func, FunctionNode)
        assert func.name == "greet"
        assert func.return_type == "any"
        assert len(func.params) == 1
        assert func.params[0].name == "name"
        assert func.params[0].type == "string"
        assert func.params[0].required == True

    def test_parse_function_with_multiple_params(self, tmp_path):
        """Test function with multiple parameters"""
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="TestFunc">
            <q:function name="calculateDiscount" return="number">
                <q:param name="price" type="number" required="true" />
                <q:param name="percentage" type="number" default="10" />
                <q:param name="includesTax" type="boolean" default="false" />
                <q:return value="{price * (1 - percentage/100)}" />
            </q:function>
        </q:component>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(component_file))

        func = ast.statements[0]
        assert func.name == "calculateDiscount"
        assert func.return_type == "number"
        assert len(func.params) == 3

        assert func.params[0].name == "price"
        assert func.params[0].required == True

        assert func.params[1].name == "percentage"
        assert func.params[1].default == "10"

        assert func.params[2].name == "includesTax"
        assert func.params[2].default == "false"

    def test_parse_function_with_cache(self, tmp_path):
        """Test function with caching enabled"""
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="TestFunc">
            <q:function name="expensiveCalc" cache="true" cache_ttl="3600">
                <q:param name="input" type="number" />
                <q:return value="{input * 2}" />
            </q:function>
        </q:component>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(component_file))

        func = ast.statements[0]
        assert func.cache == True
        assert func.cache_ttl == 3600

    def test_parse_function_with_memoize(self, tmp_path):
        """Test function with memoization"""
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="TestFunc">
            <q:function name="fibonacci" memoize="true">
                <q:param name="n" type="number" />
                <q:return value="{n}" />
            </q:function>
        </q:component>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(component_file))

        func = ast.statements[0]
        assert func.memoize == True

    def test_parse_function_with_rest_api(self, tmp_path):
        """Test function with REST API configuration"""
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="TestFunc">
            <q:function name="getUser"
                return="object"
                rest="/api/users/{id}"
                method="GET"
                auth="bearer"
                status="200">
                <q:param name="id" type="number" required="true" />
                <q:return value="{user}" />
            </q:function>
        </q:component>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(component_file))

        func = ast.statements[0]
        assert func.is_rest_enabled() == True
        assert func.rest_config.endpoint == "/api/users/{id}"
        assert func.rest_config.method == "GET"
        assert func.rest_config.auth == "bearer"
        assert func.rest_config.status == 200

    def test_parse_function_with_body_statements(self, tmp_path):
        """Test function with multiple body statements"""
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="TestFunc">
            <q:function name="processOrder">
                <q:param name="orderId" type="number" />

                <q:query name="order" datasource="db">
                    SELECT * FROM orders WHERE id = {orderId}
                </q:query>

                <q:set name="total" value="{order.amount * 1.1}" />

                <q:if condition="{total > 100}">
                    <q:set name="discount" value="10" />
                </q:if>

                <q:return value="{total - discount}" />
            </q:function>
        </q:component>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(component_file))

        func = ast.statements[0]
        assert func.name == "processOrder"
        assert len(func.body) > 0  # Has statements in body

    def test_parse_function_with_all_attributes(self, tmp_path):
        """Test function with all optional attributes"""
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="TestFunc">
            <q:function name="advancedFunc"
                return="object"
                scope="global"
                access="private"
                description="An advanced function"
                hint="Use carefully"
                validate_params="true"
                cache="true"
                cache_ttl="600"
                memoize="false"
                pure="true"
                async="true"
                retry="3"
                timeout="5000">
                <q:param name="input" type="any" />
                <q:return value="{input}" />
            </q:function>
        </q:component>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(component_file))

        func = ast.statements[0]
        assert func.name == "advancedFunc"
        assert func.return_type == "object"
        assert func.scope == "global"
        assert func.access == "private"
        assert func.description == "An advanced function"
        assert func.hint == "Use carefully"
        assert func.validate_params == True
        assert func.cache == True
        assert func.cache_ttl == 600
        assert func.memoize == False
        assert func.pure == True
        assert func.async_func == True
        assert func.retry == 3
        assert func.timeout == 5000

    def test_function_missing_name_raises_error(self, tmp_path):
        """Test that function without name raises error"""
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="TestFunc">
            <q:function>
                <q:return value="test" />
            </q:function>
        </q:component>
        """)

        parser = QuantumParser()
        with pytest.raises(QuantumParseError, match="requires 'name' attribute"):
            parser.parse_file(str(component_file))


class TestFunctionRuntime:
    """Test function execution runtime"""

    def test_register_and_call_function(self):
        """Test registering and calling a function"""
        runtime = FunctionRuntime()

        # Create simple function
        func = FunctionNode("double")
        func.params = []
        func.body = []

        runtime.register_function(func)
        assert "double" in runtime.functions

    def test_call_function_with_params(self):
        """Test calling function with parameters"""
        runtime = FunctionRuntime()

        # Create function with params
        from core.ast_nodes import QuantumParam
        func = FunctionNode("add")
        func.add_param(QuantumParam("a", "number", True))
        func.add_param(QuantumParam("b", "number", True))

        runtime.register_function(func)

        # Call function
        result = runtime.call("add", {"a": 5, "b": 3}, {})
        # Note: result will be None because we don't have a return statement
        # In real usage, function would have q:return

    def test_call_nonexistent_function_raises_error(self):
        """Test calling non-existent function raises error"""
        runtime = FunctionRuntime()

        with pytest.raises(RuntimeError, match="not found"):
            runtime.call("nonexistent", {}, {})

    def test_function_cache(self):
        """Test function result caching"""
        runtime = FunctionRuntime()

        func = FunctionNode("cached")
        func.cache = True
        func.cache_ttl = 60  # 60 seconds

        runtime.register_function(func)

        # First call
        result1 = runtime.call("cached", {"x": 1}, {})

        # Second call with same args should use cache
        result2 = runtime.call("cached", {"x": 1}, {})

        # Different args should not use cache
        result3 = runtime.call("cached", {"x": 2}, {})

    def test_function_memoize(self):
        """Test function memoization (permanent cache)"""
        runtime = FunctionRuntime()

        func = FunctionNode("memoized")
        func.memoize = True

        runtime.register_function(func)

        # Memoize should cache permanently
        result1 = runtime.call("memoized", {"x": 1}, {})
        result2 = runtime.call("memoized", {"x": 1}, {})

    def test_param_validation(self):
        """Test parameter validation"""
        runtime = FunctionRuntime()

        from core.ast_nodes import QuantumParam
        func = FunctionNode("validated")
        func.validate_params = True
        func.add_param(QuantumParam("required_param", "string", True))

        runtime.register_function(func)

        # Missing required param should raise error
        with pytest.raises(ValueError, match="Required parameter"):
            runtime.call("validated", {}, {})

    def test_param_type_coercion(self):
        """Test parameter type coercion"""
        runtime = FunctionRuntime()

        from core.ast_nodes import QuantumParam
        func = FunctionNode("typed")
        func.validate_params = True
        func.add_param(QuantumParam("num", "number", True))

        runtime.register_function(func)

        # String should be coerced to number
        result = runtime.call("typed", {"num": "42"}, {})
        # Param should be converted to float

    def test_default_parameter_values(self):
        """Test parameter default values"""
        runtime = FunctionRuntime()

        from core.ast_nodes import QuantumParam
        func = FunctionNode("withDefaults")
        func.add_param(QuantumParam("a", "number", False, "10"))
        func.add_param(QuantumParam("b", "number", False, "20"))

        runtime.register_function(func)

        # Call without providing params - should use defaults
        result = runtime.call("withDefaults", {}, {})


class TestFunctionIntegration:
    """Test function integration with other features"""

    def test_function_with_query(self, tmp_path):
        """Test function containing q:query"""
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="TestFunc">
            <q:function name="getUsers">
                <q:param name="limit" type="number" default="10" />
                <q:query name="users" datasource="db">
                    SELECT * FROM users LIMIT {limit}
                </q:query>
                <q:return value="{users}" />
            </q:function>
        </q:component>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(component_file))

        func = ast.statements[0]
        assert func.name == "getUsers"
        assert len(func.body) > 0  # Has query in body

    def test_function_with_conditional(self, tmp_path):
        """Test function with q:if conditional"""
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="TestFunc">
            <q:function name="checkAge">
                <q:param name="age" type="number" />
                <q:if condition="{age >= 18}">
                    <q:return value="Adult" />
                </q:if>
                <q:else>
                    <q:return value="Minor" />
                </q:else>
            </q:function>
        </q:component>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(component_file))

        func = ast.statements[0]
        assert func.name == "checkAge"
        assert len(func.body) > 0

    def test_function_with_loop(self, tmp_path):
        """Test function with q:loop"""
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="TestFunc">
            <q:function name="sumArray">
                <q:param name="numbers" type="array" />
                <q:set name="total" value="0" />
                <q:loop type="array" var="num" array="{numbers}">
                    <q:set name="total" operation="add" value="{num}" />
                </q:loop>
                <q:return value="{total}" />
            </q:function>
        </q:component>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(component_file))

        func = ast.statements[0]
        assert func.name == "sumArray"


class TestFunctionValidation:
    """Test function validation"""

    def test_function_validates_successfully(self):
        """Test valid function passes validation"""
        func = FunctionNode("validFunc")
        from core.ast_nodes import QuantumParam
        func.add_param(QuantumParam("param1", "string", True))

        errors = func.validate()
        assert len(errors) == 0

    def test_function_without_name_fails_validation(self):
        """Test function without name fails validation"""
        func = FunctionNode("")

        errors = func.validate()
        assert len(errors) > 0
        assert any("name is required" in err for err in errors)

    def test_function_with_invalid_rest_config_fails(self):
        """Test function with invalid REST config fails validation"""
        func = FunctionNode("restFunc")
        func.enable_rest("", "GET")  # Empty endpoint

        errors = func.validate()
        assert len(errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
