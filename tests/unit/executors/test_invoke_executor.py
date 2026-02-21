"""
Tests for InvokeExecutor - q:invoke function/component/HTTP invocation

Coverage target: 18% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Any, Dict, List

from runtime.executors.data.invoke_executor import InvokeExecutor
from runtime.executors.base import ExecutorError
from core.features.invocation.src.ast_node import InvokeNode

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


# =============================================================================
# Mock Objects for Invocation Service
# =============================================================================

@dataclass
class MockInvokeResult:
    """Mock invocation result"""
    success: bool = True
    data: Any = None
    error: str = None
    execution_time: int = 0
    invocation_type: str = "function"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MockInvocationService:
    """Mock invocation service"""

    def __init__(self):
        self.last_type = None
        self.last_params = None
        self._cache = {}
        self._results = {}

    def set_result(self, key: str, result: MockInvokeResult):
        """Set mock result"""
        self._results[key] = result

    def invoke(self, invocation_type: str, params: Dict[str, Any], context=None) -> MockInvokeResult:
        """Mock invoke"""
        self.last_type = invocation_type
        self.last_params = params

        key = f"{invocation_type}:{params.get('function', params.get('component', params.get('url', '')))}"
        if key in self._results:
            return self._results[key]

        return MockInvokeResult(success=True, data={"result": "ok"}, invocation_type=invocation_type)

    def get_from_cache(self, key: str):
        """Get cached result"""
        return self._cache.get(key)

    def put_in_cache(self, key: str, result, ttl: int):
        """Cache result"""
        self._cache[key] = result


class MockInvokeRuntime(MockRuntime):
    """Extended mock runtime with invocation service"""

    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._invocation_service = MockInvocationService()
        self._services = MagicMock()
        self._services.invocation = self._invocation_service

    @property
    def services(self):
        return self._services


# =============================================================================
# Mock Param and Header Nodes
# =============================================================================

@dataclass
class MockParamNode:
    """Mock parameter node"""
    name: str
    default: str = None
    param_type: str = "string"


@dataclass
class MockHeaderNode:
    """Mock HTTP header node"""
    name: str
    value: str


# =============================================================================
# Test Classes
# =============================================================================

class TestInvokeExecutorBasic:
    """Basic functionality tests"""

    def test_handles_invoke_node(self):
        """Test that InvokeExecutor handles InvokeNode"""
        runtime = MockInvokeRuntime()
        executor = InvokeExecutor(runtime)
        assert InvokeNode in executor.handles

    def test_handles_returns_list(self):
        """Test that handles returns a list"""
        runtime = MockInvokeRuntime()
        executor = InvokeExecutor(runtime)
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestFunctionInvocation:
    """Test function invocation"""

    def test_invoke_function_basic(self):
        """Test basic function invocation"""
        runtime = MockInvokeRuntime()
        runtime._invocation_service.set_result("function:calculateSum", MockInvokeResult(
            success=True,
            data=42,
            invocation_type="function"
        ))
        executor = InvokeExecutor(runtime)

        node = InvokeNode("result")
        node.function = "calculateSum"

        executor.execute(node, runtime.execution_context)

        assert runtime._invocation_service.last_type == "function"
        assert runtime._invocation_service.last_params["function"] == "calculateSum"

    def test_invoke_function_with_params(self):
        """Test function invocation with parameters"""
        runtime = MockInvokeRuntime({"a": 10, "b": 20})
        executor = InvokeExecutor(runtime)

        node = InvokeNode("result")
        node.function = "add"
        node.params = [
            MockParamNode("x", "{a}"),
            MockParamNode("y", "{b}")
        ]

        executor.execute(node, runtime.execution_context)

        params = runtime._invocation_service.last_params
        assert params["args"]["x"] == 10
        assert params["args"]["y"] == 20


class TestComponentInvocation:
    """Test component invocation"""

    def test_invoke_component_basic(self):
        """Test basic component invocation"""
        runtime = MockInvokeRuntime()
        runtime._invocation_service.set_result("component:UserProfile", MockInvokeResult(
            success=True,
            data={"html": "<div>Profile</div>"},
            invocation_type="component"
        ))
        executor = InvokeExecutor(runtime)

        node = InvokeNode("profile")
        node.component = "UserProfile"

        executor.execute(node, runtime.execution_context)

        assert runtime._invocation_service.last_type == "component"
        assert runtime._invocation_service.last_params["component"] == "UserProfile"

    def test_invoke_component_with_params(self):
        """Test component invocation with parameters"""
        runtime = MockInvokeRuntime({"userId": 123})
        executor = InvokeExecutor(runtime)

        node = InvokeNode("profile")
        node.component = "UserProfile"
        node.params = [MockParamNode("id", "{userId}")]

        executor.execute(node, runtime.execution_context)

        params = runtime._invocation_service.last_params
        assert params["args"]["id"] == 123


class TestHTTPInvocation:
    """Test HTTP invocation"""

    def test_invoke_http_basic(self):
        """Test basic HTTP GET invocation"""
        runtime = MockInvokeRuntime()
        runtime._invocation_service.set_result("http:https://api.example.com/users", MockInvokeResult(
            success=True,
            data=[{"id": 1, "name": "Test"}],
            invocation_type="http"
        ))
        executor = InvokeExecutor(runtime)

        node = InvokeNode("users")
        node.url = "https://api.example.com/users"
        node.method = "GET"

        executor.execute(node, runtime.execution_context)

        assert runtime._invocation_service.last_type == "http"
        assert runtime._invocation_service.last_params["url"] == "https://api.example.com/users"
        assert runtime._invocation_service.last_params["method"] == "GET"

    def test_invoke_http_with_headers(self):
        """Test HTTP invocation with headers"""
        runtime = MockInvokeRuntime({"apiKey": "secret123"})
        executor = InvokeExecutor(runtime)

        node = InvokeNode("data")
        node.url = "https://api.example.com/data"
        node.method = "GET"
        node.headers = [
            MockHeaderNode("Authorization", "Bearer {apiKey}"),
            MockHeaderNode("Accept", "application/json")
        ]

        executor.execute(node, runtime.execution_context)

        params = runtime._invocation_service.last_params
        assert params["headers"]["Authorization"] == "Bearer secret123"
        assert params["headers"]["Accept"] == "application/json"

    def test_invoke_http_post_with_body(self):
        """Test HTTP POST with body"""
        runtime = MockInvokeRuntime({"userName": "test"})
        executor = InvokeExecutor(runtime)

        node = InvokeNode("result")
        node.url = "https://api.example.com/users"
        node.method = "POST"
        node.body = '{"name": "{userName}"}'
        node.content_type = "application/json"

        executor.execute(node, runtime.execution_context)

        params = runtime._invocation_service.last_params
        assert params["method"] == "POST"
        assert params["body"] is not None

    def test_invoke_http_with_query_params(self):
        """Test HTTP with query parameters"""
        runtime = MockInvokeRuntime({"page": 2})
        executor = InvokeExecutor(runtime)

        node = InvokeNode("results")
        node.url = "https://api.example.com/search"
        node.method = "GET"
        node.params = [
            MockParamNode("page", "{page}"),
            MockParamNode("limit", "20")
        ]

        executor.execute(node, runtime.execution_context)

        params = runtime._invocation_service.last_params
        assert params["params"]["page"] == 2
        assert params["params"]["limit"] == "20"

    def test_invoke_http_with_auth(self):
        """Test HTTP with authentication"""
        runtime = MockInvokeRuntime({"token": "mytoken"})
        executor = InvokeExecutor(runtime)

        node = InvokeNode("data")
        node.url = "https://api.example.com/secure"
        node.method = "GET"
        node.auth_type = "bearer"
        node.auth_token = "{token}"

        executor.execute(node, runtime.execution_context)

        params = runtime._invocation_service.last_params
        assert params["auth_type"] == "bearer"
        assert params["auth_token"] == "mytoken"

    def test_invoke_http_with_timeout_and_retry(self):
        """Test HTTP with timeout and retry settings"""
        runtime = MockInvokeRuntime()
        executor = InvokeExecutor(runtime)

        node = InvokeNode("data")
        node.url = "https://api.example.com/slow"
        node.method = "GET"
        node.timeout = 30
        node.retry = 3
        node.retry_delay = 1000

        executor.execute(node, runtime.execution_context)

        params = runtime._invocation_service.last_params
        assert params["timeout"] == 30
        assert params["retry"] == 3
        assert params["retry_delay"] == 1000


class TestCaching:
    """Test invocation caching"""

    def test_cache_hit_returns_cached(self):
        """Test that cache hit returns cached result"""
        runtime = MockInvokeRuntime()
        cached_result = MockInvokeResult(success=True, data={"cached": True})
        runtime._invocation_service._cache["invoke_result_test"] = cached_result
        executor = InvokeExecutor(runtime)

        node = InvokeNode("result")
        node.function = "test"
        node.cache = True

        # Patch get_from_cache to return cached result
        runtime._invocation_service.get_from_cache = MagicMock(return_value=cached_result)

        executor.execute(node, runtime.execution_context)

        # Verify cache was checked
        runtime._invocation_service.get_from_cache.assert_called()

    def test_cache_miss_calls_invoke(self):
        """Test that cache miss calls invoke"""
        runtime = MockInvokeRuntime()
        executor = InvokeExecutor(runtime)

        node = InvokeNode("result")
        node.function = "test"
        node.cache = True

        executor.execute(node, runtime.execution_context)

        # Verify invoke was called
        assert runtime._invocation_service.last_type == "function"

    def test_cache_stores_successful_result(self):
        """Test that successful result is cached"""
        runtime = MockInvokeRuntime()
        executor = InvokeExecutor(runtime)

        node = InvokeNode("result")
        node.function = "test"
        node.cache = True
        node.ttl = 3600

        put_cache = MagicMock()
        runtime._invocation_service.put_in_cache = put_cache

        executor.execute(node, runtime.execution_context)

        put_cache.assert_called_once()


class TestResultStorage:
    """Test result storage"""

    def test_stores_data_in_variable(self):
        """Test that data is stored in named variable"""
        runtime = MockInvokeRuntime()
        runtime._invocation_service.set_result("function:getData", MockInvokeResult(
            success=True,
            data={"key": "value"}
        ))
        executor = InvokeExecutor(runtime)

        node = InvokeNode("myData")
        node.function = "getData"

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("myData")
        assert stored == {"key": "value"}

    def test_stores_result_metadata(self):
        """Test that result metadata is stored"""
        runtime = MockInvokeRuntime()
        runtime._invocation_service.set_result("function:test", MockInvokeResult(
            success=True,
            data="result",
            execution_time=50,
            invocation_type="function",
            metadata={"extra": "info"}
        ))
        executor = InvokeExecutor(runtime)

        node = InvokeNode("result")
        node.function = "test"

        executor.execute(node, runtime.execution_context)

        metadata = runtime.execution_context.get_variable("result_result")
        assert metadata["success"] is True
        assert metadata["executionTime"] == 50
        assert metadata["invocationType"] == "function"

    def test_custom_result_variable(self):
        """Test storing in custom result variable"""
        runtime = MockInvokeRuntime()
        executor = InvokeExecutor(runtime)

        node = InvokeNode("invoke")
        node.function = "test"
        node.result = "customMeta"

        executor.execute(node, runtime.execution_context)

        custom = runtime.execution_context.get_variable("customMeta")
        assert custom is not None


class TestInvocationTypeDetection:
    """Test invocation type detection"""

    def test_unknown_type_raises_error(self):
        """Test that unknown invocation type raises error"""
        runtime = MockInvokeRuntime()
        executor = InvokeExecutor(runtime)

        node = InvokeNode("result")
        # No function, component, url, endpoint, or service set

        with pytest.raises(ExecutorError, match="requires one of"):
            executor.execute(node, runtime.execution_context)


class TestErrorHandling:
    """Test error handling"""

    def test_invoke_error_wrapped(self):
        """Test that invocation error is wrapped"""
        runtime = MockInvokeRuntime()
        runtime._invocation_service.invoke = MagicMock(side_effect=Exception("Network error"))
        executor = InvokeExecutor(runtime)

        node = InvokeNode("result")
        node.url = "https://api.example.com/fail"
        node.method = "GET"

        with pytest.raises(ExecutorError, match="Invoke execution error in 'result'"):
            executor.execute(node, runtime.execution_context)


class TestContentTypeHandling:
    """Test content-type handling"""

    def test_default_content_type_added(self):
        """Test that default Content-Type is added"""
        runtime = MockInvokeRuntime()
        executor = InvokeExecutor(runtime)

        node = InvokeNode("result")
        node.url = "https://api.example.com/data"
        node.method = "POST"
        node.content_type = "application/json"
        node.headers = []

        executor.execute(node, runtime.execution_context)

        params = runtime._invocation_service.last_params
        assert params["headers"]["Content-Type"] == "application/json"

    def test_custom_content_type_not_overwritten(self):
        """Test that custom Content-Type is not overwritten"""
        runtime = MockInvokeRuntime()
        executor = InvokeExecutor(runtime)

        node = InvokeNode("result")
        node.url = "https://api.example.com/data"
        node.method = "POST"
        node.content_type = "application/json"
        node.headers = [MockHeaderNode("Content-Type", "text/xml")]

        executor.execute(node, runtime.execution_context)

        params = runtime._invocation_service.last_params
        assert params["headers"]["Content-Type"] == "text/xml"


class TestJSONBodyParsing:
    """Test JSON body parsing"""

    def test_json_body_parsed(self):
        """Test that JSON array body is parsed"""
        runtime = MockInvokeRuntime()
        executor = InvokeExecutor(runtime)

        node = InvokeNode("result")
        node.url = "https://api.example.com/data"
        node.method = "POST"
        # Use array JSON to avoid databinding interference with curly braces
        node.body = '[1, 2, 3]'
        node.content_type = "application/json"

        executor.execute(node, runtime.execution_context)

        params = runtime._invocation_service.last_params
        # Body should be parsed to list
        assert params["body"] == [1, 2, 3]

    def test_invalid_json_body_kept_as_string(self):
        """Test that invalid JSON body is kept as string"""
        runtime = MockInvokeRuntime()
        executor = InvokeExecutor(runtime)

        node = InvokeNode("result")
        node.url = "https://api.example.com/data"
        node.method = "POST"
        node.body = "not valid json"
        node.content_type = "application/json"

        executor.execute(node, runtime.execution_context)

        params = runtime._invocation_service.last_params
        # Invalid JSON stays as string
        assert params["body"] == "not valid json"
