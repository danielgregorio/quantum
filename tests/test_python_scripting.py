"""
Tests for Python Scripting Feature (q:python, q:pyimport, q:class, q:decorator)

This tests the ColdFusion-inspired Python embedding in Quantum components.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

from core.ast_nodes import (
    PythonNode, PyImportNode, PyClassNode, PyDecoratorNode, PyExprNode
)
from runtime.python_bridge import QuantumBridge, QuantumBridgeError


# =============================================================================
# QuantumBridge Tests
# =============================================================================

class TestQuantumBridge:
    """Tests for the QuantumBridge (the magical 'q' object)"""

    def test_bridge_creation(self):
        """Test creating a bridge with context"""
        context = {'user_id': 123, 'name': 'Alice'}
        bridge = QuantumBridge(context)

        assert bridge._context == context
        assert bridge._services == {}

    def test_bridge_get_variable(self):
        """Test accessing variables via q.variable"""
        context = {'user_id': 123, 'items': [1, 2, 3]}
        bridge = QuantumBridge(context)

        assert bridge.user_id == 123
        assert bridge.items == [1, 2, 3]

    def test_bridge_set_variable(self):
        """Test setting variables via q.variable = value"""
        context = {}
        bridge = QuantumBridge(context)

        bridge.result = 42
        bridge.message = "Hello"

        # When context is a dict, variables are stored there
        assert context['result'] == 42
        assert context['message'] == "Hello"

    def test_bridge_export_method(self):
        """Test q.export() method"""
        context = {}
        bridge = QuantumBridge(context)

        bridge.export('data', {'key': 'value'})

        assert bridge._exports['data'] == {'key': 'value'}
        assert bridge.data == {'key': 'value'}

    def test_bridge_with_services(self):
        """Test bridge with services dict"""
        mock_db = Mock()
        mock_cache = Mock()

        services = {'db': mock_db, 'cache': mock_cache}
        bridge = QuantumBridge({}, services=services)

        assert bridge._services['db'] == mock_db
        assert bridge._services['cache'] == mock_cache


class TestQuantumBridgeLogging:
    """Tests for bridge logging methods"""

    def test_log_method(self):
        """Test q.log() method"""
        bridge = QuantumBridge({})

        # Should not raise
        bridge.log("Test message")
        bridge.log("Debug", level="debug")

    def test_info_method(self):
        """Test q.info() method"""
        bridge = QuantumBridge({})
        bridge.info("Info message")

    def test_warn_method(self):
        """Test q.warn() method"""
        bridge = QuantumBridge({})
        bridge.warn("Warning message")

    def test_error_method(self):
        """Test q.error() method"""
        bridge = QuantumBridge({})
        bridge.error("Error message")


class TestQuantumBridgeUtilities:
    """Tests for bridge utility methods"""

    def test_now_method(self):
        """Test q.now() method"""
        from datetime import datetime
        bridge = QuantumBridge({})

        result = bridge.now()
        assert isinstance(result, datetime)

    def test_uuid_method(self):
        """Test q.uuid() method"""
        bridge = QuantumBridge({})

        result = bridge.uuid()
        assert isinstance(result, str)
        assert len(result) == 36  # UUID format

    def test_json_method(self):
        """Test q.json() method"""
        bridge = QuantumBridge({})

        data = {'name': 'Alice', 'age': 30}
        result = bridge.json(data)

        assert result == '{"name": "Alice", "age": 30}'


# =============================================================================
# AST Node Tests
# =============================================================================

class TestPythonNodes:
    """Tests for Python AST nodes"""

    def test_python_node_creation(self):
        """Test creating PythonNode"""
        node = PythonNode(
            code="result = 1 + 1",
            scope="component",
            async_mode=False,
            result="result"
        )

        assert node.code == "result = 1 + 1"
        assert node.scope == "component"
        assert node.async_mode is False
        assert node.result == "result"

    def test_python_node_defaults(self):
        """Test PythonNode default values"""
        node = PythonNode(code="x = 1")

        assert node.scope == "component"
        assert node.async_mode is False
        assert node.timeout is None
        assert node.result is None

    def test_pyimport_node(self):
        """Test creating PyImportNode"""
        node = PyImportNode(
            module="pandas",
            alias="pd"
        )

        assert node.module == "pandas"
        assert node.alias == "pd"
        assert node.names == []

    def test_pyimport_node_with_names(self):
        """Test PyImportNode with specific imports"""
        node = PyImportNode(
            module="numpy",
            names=["array", "zeros", "ones"]
        )

        assert node.module == "numpy"
        assert node.names == ["array", "zeros", "ones"]

    def test_pyclass_node(self):
        """Test creating PyClassNode"""
        node = PyClassNode(
            name="UserValidator",
            code="def validate(self): pass",
            bases=["BaseValidator"],
            decorators=["dataclass"]
        )

        assert node.name == "UserValidator"
        assert "validate" in node.code
        assert node.bases == ["BaseValidator"]
        assert node.decorators == ["dataclass"]

    def test_pydecorator_node(self):
        """Test creating PyDecoratorNode"""
        node = PyDecoratorNode(
            name="cached",
            code="def wrapper(*args): return func(*args)\nreturn wrapper",
            params=["ttl"]
        )

        assert node.name == "cached"
        assert node.params == ["ttl"]

    def test_pyexpr_node(self):
        """Test creating PyExprNode"""
        node = PyExprNode(
            expr="user.name.upper()",
            format_spec=".2f"
        )

        assert node.expr == "user.name.upper()"
        assert node.format_spec == ".2f"


# =============================================================================
# Integration Tests (with mock component)
# =============================================================================

class TestPythonExecution:
    """Integration tests for Python execution"""

    @pytest.fixture
    def mock_component(self):
        """Create a mock component for testing"""
        from runtime.execution_context import ExecutionContext

        component = Mock()
        component.context = {}
        component.database_service = None
        component.cache_service = None
        component.message_queue_service = None
        component.job_executor = None

        return component

    def test_simple_python_execution(self, mock_component):
        """Test simple Python code execution"""
        from runtime.python_bridge import QuantumBridge

        code = """
result = 1 + 1
q.answer = result
"""

        q = QuantumBridge(mock_component.context)
        namespace = {'q': q, '__builtins__': __builtins__}

        exec(code, namespace)

        # When context is a dict, variables are stored there
        assert mock_component.context['answer'] == 2

    def test_python_with_context_variables(self, mock_component):
        """Test Python code accessing context variables"""
        from runtime.python_bridge import QuantumBridge

        mock_component.context = {'price': 100, 'quantity': 5}

        code = """
total = q.price * q.quantity
q.total = total
"""

        q = QuantumBridge(mock_component.context)
        namespace = {'q': q, '__builtins__': __builtins__}

        exec(code, namespace)

        assert mock_component.context['total'] == 500

    def test_python_with_loops(self, mock_component):
        """Test Python code with loops"""
        from runtime.python_bridge import QuantumBridge

        context = {}
        code = """
items = [1, 2, 3, 4, 5]
q.sum = sum(items)
q.doubled = [x * 2 for x in items]
"""

        q = QuantumBridge(context)
        namespace = {'q': q, '__builtins__': __builtins__}

        exec(code, namespace)

        assert context['sum'] == 15
        assert context['doubled'] == [2, 4, 6, 8, 10]

    def test_python_with_functions(self, mock_component):
        """Test Python code with function definitions"""
        from runtime.python_bridge import QuantumBridge

        context = {}
        code = """
def calculate_discount(price, percent):
    return price * (1 - percent / 100)

original = 100
q.discounted = calculate_discount(original, 20)
"""

        q = QuantumBridge(context)
        namespace = {'q': q, '__builtins__': __builtins__}

        exec(code, namespace)

        assert context['discounted'] == 80.0

    def test_python_with_classes(self, mock_component):
        """Test Python code with class definitions"""
        from runtime.python_bridge import QuantumBridge

        context = {}
        code = """
class Calculator:
    def add(self, a, b):
        return a + b

    def multiply(self, a, b):
        return a * b

calc = Calculator()
q.result = calc.add(3, 4)
"""

        q = QuantumBridge(context)
        namespace = {'q': q, '__builtins__': __builtins__}

        exec(code, namespace)

        assert context['result'] == 7

    def test_python_with_json(self, mock_component):
        """Test Python code with JSON processing"""
        from runtime.python_bridge import QuantumBridge
        import json

        context = {}
        code = """
import json

data = '{"name": "Alice", "age": 30}'
parsed = json.loads(data)
q.name = parsed['name']
q.age = parsed['age']
"""

        q = QuantumBridge(context)
        namespace = {'q': q, '__builtins__': __builtins__}

        exec(code, namespace)

        assert context['name'] == "Alice"
        assert context['age'] == 30


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestPythonErrorHandling:
    """Tests for error handling in Python execution"""

    def test_syntax_error(self):
        """Test handling of Python syntax errors"""
        from runtime.python_bridge import QuantumBridge

        code = "def broken("  # Invalid syntax

        q = QuantumBridge({})
        namespace = {'q': q, '__builtins__': __builtins__}

        with pytest.raises(SyntaxError):
            exec(code, namespace)

    def test_runtime_error(self):
        """Test handling of Python runtime errors"""
        from runtime.python_bridge import QuantumBridge

        code = "result = 1 / 0"  # Division by zero

        q = QuantumBridge({})
        namespace = {'q': q, '__builtins__': __builtins__}

        with pytest.raises(ZeroDivisionError):
            exec(code, namespace)

    def test_undefined_variable(self):
        """Test handling of undefined variable access"""
        from runtime.python_bridge import QuantumBridge

        code = "result = undefined_var"

        q = QuantumBridge({})
        namespace = {'q': q, '__builtins__': __builtins__}

        with pytest.raises(NameError):
            exec(code, namespace)


# =============================================================================
# Security Tests
# =============================================================================

class TestPythonSecurity:
    """Tests for Python execution security"""

    def test_isolated_namespace(self):
        """Test that execution uses isolated namespace"""
        from runtime.python_bridge import QuantumBridge

        # Define something in one execution
        code1 = "secret = 'password123'"
        q1 = QuantumBridge({})
        ns1 = {'q': q1, '__builtins__': __builtins__}
        exec(code1, ns1)

        # Should not be accessible in another execution
        code2 = "q.result = 'safe'"
        q2 = QuantumBridge({})
        ns2 = {'q': q2, '__builtins__': __builtins__}
        exec(code2, ns2)

        assert 'secret' not in ns2


# =============================================================================
# Parser Tests (Integration)
# =============================================================================

class TestPythonParser:
    """Tests for parsing Python-related tags"""

    def test_parse_python_tag(self):
        """Test parsing q:python tag"""
        from core.parser import QuantumParser

        xml = """<?xml version="1.0" encoding="UTF-8"?>
<q:component name="PythonTest">
    <q:python>
        result = 1 + 1
        q.answer = result
    </q:python>
</q:component>
"""
        parser = QuantumParser()
        ast = parser.parse(xml)

        # Find the Python node
        python_nodes = [n for n in ast.statements if isinstance(n, PythonNode)]
        assert len(python_nodes) == 1
        assert "result = 1 + 1" in python_nodes[0].code

    def test_parse_python_with_attributes(self):
        """Test parsing q:python with attributes"""
        from core.parser import QuantumParser

        xml = """<?xml version="1.0" encoding="UTF-8"?>
<q:component name="PythonTest">
    <q:python scope="isolated" result="output" timeout="30s">
        q.output = calculate()
    </q:python>
</q:component>
"""
        parser = QuantumParser()
        ast = parser.parse(xml)

        python_nodes = [n for n in ast.statements if isinstance(n, PythonNode)]
        assert len(python_nodes) == 1
        assert python_nodes[0].scope == "isolated"
        assert python_nodes[0].result == "output"
        assert python_nodes[0].timeout == "30s"

    def test_parse_pyimport_tag(self):
        """Test parsing q:pyimport tag"""
        from core.parser import QuantumParser

        xml = """<?xml version="1.0" encoding="UTF-8"?>
<q:component name="ImportTest">
    <q:pyimport module="pandas" as="pd" />
</q:component>
"""
        parser = QuantumParser()
        ast = parser.parse(xml)

        import_nodes = [n for n in ast.statements if isinstance(n, PyImportNode)]
        assert len(import_nodes) == 1
        assert import_nodes[0].module == "pandas"
        assert import_nodes[0].alias == "pd"

    def test_parse_pyimport_with_names(self):
        """Test parsing q:pyimport with specific names"""
        from core.parser import QuantumParser

        xml = """<?xml version="1.0" encoding="UTF-8"?>
<q:component name="ImportTest">
    <q:pyimport module="os.path" names="join,exists,dirname" />
</q:component>
"""
        parser = QuantumParser()
        ast = parser.parse(xml)

        import_nodes = [n for n in ast.statements if isinstance(n, PyImportNode)]
        assert len(import_nodes) == 1
        assert import_nodes[0].module == "os.path"
        assert import_nodes[0].names == ["join", "exists", "dirname"]

    def test_parse_pyclass_tag(self):
        """Test parsing q:class tag"""
        from core.parser import QuantumParser

        xml = """<?xml version="1.0" encoding="UTF-8"?>
<q:component name="ClassTest">
    <q:class name="UserValidator" bases="object">
        def validate(self, data):
            return bool(data.get('email'))
    </q:class>
</q:component>
"""
        parser = QuantumParser()
        ast = parser.parse(xml)

        class_nodes = [n for n in ast.statements if isinstance(n, PyClassNode)]
        assert len(class_nodes) == 1
        assert class_nodes[0].name == "UserValidator"
        assert "validate" in class_nodes[0].code

    def test_parse_pydecorator_tag(self):
        """Test parsing q:decorator tag"""
        from core.parser import QuantumParser

        xml = """<?xml version="1.0" encoding="UTF-8"?>
<q:component name="DecoratorTest">
    <q:decorator name="cached" params="ttl">
        cache = {}
        def wrapper(*args):
            return func(*args)
        return wrapper
    </q:decorator>
</q:component>
"""
        parser = QuantumParser()
        ast = parser.parse(xml)

        decorator_nodes = [n for n in ast.statements if isinstance(n, PyDecoratorNode)]
        assert len(decorator_nodes) == 1
        assert decorator_nodes[0].name == "cached"
        assert decorator_nodes[0].params == ["ttl"]
