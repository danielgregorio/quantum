"""
Tests for DataExecutor - q:data import execution

Coverage target: 21% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Any, Dict, List

from runtime.executors.data.data_executor import DataExecutor
from runtime.executors.base import ExecutorError
from core.ast_nodes import DataNode

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


# =============================================================================
# Mock Objects for Data Import Service
# =============================================================================

@dataclass
class MockDataResult:
    """Mock data import result"""
    success: bool = True
    data: List[Dict[str, Any]] = None
    error: str = None
    recordCount: int = 0
    loadTime: int = 0
    cached: bool = False
    source: str = ""

    def __post_init__(self):
        if self.data is None:
            self.data = []


class MockDataImportService:
    """Mock data import service"""

    def __init__(self):
        self.last_type = None
        self.last_source = None
        self.last_params = None
        self._results = {}

    def set_result(self, source: str, result: MockDataResult):
        """Set mock result for a source"""
        self._results[source] = result

    def import_data(self, data_type: str, source: str, params: Dict[str, Any],
                    context=None) -> MockDataResult:
        """Mock data import"""
        self.last_type = data_type
        self.last_source = source
        self.last_params = params

        if source in self._results:
            return self._results[source]

        # Default result
        return MockDataResult(success=True, data=[], recordCount=0, source=source)


class MockDataRuntime(MockRuntime):
    """Extended mock runtime with data import service"""

    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._data_import_service = MockDataImportService()
        self._services = MagicMock()
        self._services.data_import = self._data_import_service

    @property
    def services(self):
        return self._services


# =============================================================================
# Mock Column and Field Nodes
# =============================================================================

@dataclass
class MockColumnNode:
    """Mock column definition for CSV"""
    name: str
    col_type: str = "string"
    required: bool = False
    default: Any = None


@dataclass
class MockFieldNode:
    """Mock field definition for XML"""
    name: str
    xpath: str
    field_type: str = "string"


@dataclass
class MockHeaderNode:
    """Mock HTTP header"""
    name: str
    value: str


@dataclass
class MockTransformNode:
    """Mock transform with operations"""
    operations: List[Any] = None

    def __post_init__(self):
        if self.operations is None:
            self.operations = []


@dataclass
class FilterNode:
    """Mock filter operation - named to match expected pattern"""
    condition: str


@dataclass
class SortNode:
    """Mock sort operation - named to match expected pattern"""
    by: str
    order: str = "asc"


@dataclass
class LimitNode:
    """Mock limit operation - named to match expected pattern"""
    value: int


@dataclass
class ComputeNode:
    """Mock compute operation - named to match expected pattern"""
    field: str
    expression: str
    comp_type: str = "string"


# =============================================================================
# Test Classes
# =============================================================================

class TestDataExecutorBasic:
    """Basic functionality tests"""

    def test_handles_data_node(self):
        """Test that DataExecutor handles DataNode"""
        runtime = MockDataRuntime()
        executor = DataExecutor(runtime)
        assert DataNode in executor.handles

    def test_handles_returns_list(self):
        """Test that handles returns a list"""
        runtime = MockDataRuntime()
        executor = DataExecutor(runtime)
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestCSVImport:
    """Test CSV data import"""

    def test_import_csv_basic(self):
        """Test basic CSV import"""
        runtime = MockDataRuntime()
        runtime._data_import_service.set_result("users.csv", MockDataResult(
            success=True,
            data=[
                {"id": "1", "name": "Alice"},
                {"id": "2", "name": "Bob"}
            ],
            recordCount=2,
            source="users.csv"
        ))
        executor = DataExecutor(runtime)

        node = DataNode("users", "users.csv", "csv")

        executor.execute(node, runtime.execution_context)

        # Verify data stored
        stored = runtime.execution_context.get_variable("users")
        assert len(stored) == 2
        assert stored[0]["name"] == "Alice"

    def test_import_csv_with_columns(self):
        """Test CSV import with column definitions"""
        runtime = MockDataRuntime()
        runtime._data_import_service.set_result("data.csv", MockDataResult(
            success=True,
            data=[{"id": 1, "value": 100.5}],
            recordCount=1
        ))
        executor = DataExecutor(runtime)

        node = DataNode("data", "data.csv", "csv")
        node.columns = [
            MockColumnNode("id", "integer", required=True),
            MockColumnNode("value", "decimal", required=False, default=0)
        ]

        executor.execute(node, runtime.execution_context)

        # Verify columns were passed
        params = runtime._data_import_service.last_params
        assert len(params["columns"]) == 2
        assert params["columns"][0]["name"] == "id"
        assert params["columns"][0]["type"] == "integer"
        assert params["columns"][0]["required"] is True

    def test_import_csv_with_options(self):
        """Test CSV import with custom options"""
        runtime = MockDataRuntime()
        runtime._data_import_service.set_result("data.csv", MockDataResult(success=True, data=[]))
        executor = DataExecutor(runtime)

        node = DataNode("data", "data.csv", "csv")
        node.delimiter = ";"
        node.quote = "'"
        node.header = False
        node.encoding = "latin-1"
        node.skip_rows = 2

        executor.execute(node, runtime.execution_context)

        params = runtime._data_import_service.last_params
        assert params["delimiter"] == ";"
        assert params["quote"] == "'"
        assert params["header"] is False
        assert params["encoding"] == "latin-1"
        assert params["skip_rows"] == 2


class TestJSONImport:
    """Test JSON data import"""

    def test_import_json_basic(self):
        """Test basic JSON import"""
        runtime = MockDataRuntime()
        runtime._data_import_service.set_result("api/users", MockDataResult(
            success=True,
            data=[{"id": 1, "name": "Test"}],
            recordCount=1
        ))
        executor = DataExecutor(runtime)

        node = DataNode("users", "api/users", "json")

        executor.execute(node, runtime.execution_context)

        assert runtime._data_import_service.last_type == "json"

    def test_import_json_with_headers(self):
        """Test JSON import with HTTP headers"""
        runtime = MockDataRuntime({"token": "abc123"})
        runtime._data_import_service.set_result("api/secure", MockDataResult(success=True, data=[]))
        executor = DataExecutor(runtime)

        node = DataNode("data", "api/secure", "json")
        node.headers = [
            MockHeaderNode("Authorization", "Bearer {token}"),
            MockHeaderNode("Accept", "application/json")
        ]

        executor.execute(node, runtime.execution_context)

        params = runtime._data_import_service.last_params
        assert len(params["headers"]) == 2
        assert params["headers"][0]["name"] == "Authorization"
        assert params["headers"][0]["value"] == "Bearer abc123"  # Databinding resolved


class TestXMLImport:
    """Test XML data import"""

    def test_import_xml_with_xpath(self):
        """Test XML import with XPath"""
        runtime = MockDataRuntime()
        runtime._data_import_service.set_result("data.xml", MockDataResult(success=True, data=[]))
        executor = DataExecutor(runtime)

        node = DataNode("items", "data.xml", "xml")
        node.xpath = "//item"
        node.namespace = "http://example.com/ns"

        executor.execute(node, runtime.execution_context)

        params = runtime._data_import_service.last_params
        assert params["xpath"] == "//item"
        assert params["namespace"] == "http://example.com/ns"

    def test_import_xml_with_fields(self):
        """Test XML import with field definitions"""
        runtime = MockDataRuntime()
        runtime._data_import_service.set_result("data.xml", MockDataResult(success=True, data=[]))
        executor = DataExecutor(runtime)

        node = DataNode("data", "data.xml", "xml")
        node.fields = [
            MockFieldNode("id", "@id", "integer"),
            MockFieldNode("title", "title/text()", "string")
        ]

        executor.execute(node, runtime.execution_context)

        params = runtime._data_import_service.last_params
        assert len(params["fields"]) == 2
        assert params["fields"][0]["xpath"] == "@id"


class TestCaching:
    """Test data caching"""

    def test_cache_enabled(self):
        """Test cache parameter is passed"""
        runtime = MockDataRuntime()
        runtime._data_import_service.set_result("data.csv", MockDataResult(success=True, data=[]))
        executor = DataExecutor(runtime)

        node = DataNode("data", "data.csv", "csv")
        node.cache = True
        node.ttl = 3600

        executor.execute(node, runtime.execution_context)

        params = runtime._data_import_service.last_params
        assert params["cache"] is True
        assert params["ttl"] == 3600

    def test_cache_disabled(self):
        """Test cache can be disabled"""
        runtime = MockDataRuntime()
        runtime._data_import_service.set_result("data.csv", MockDataResult(success=True, data=[]))
        executor = DataExecutor(runtime)

        node = DataNode("data", "data.csv", "csv")
        node.cache = False

        executor.execute(node, runtime.execution_context)

        params = runtime._data_import_service.last_params
        assert params["cache"] is False


class TestTransformations:
    """Test data transformations"""

    def test_filter_transform(self):
        """Test filter transformation"""
        runtime = MockDataRuntime()
        runtime._data_import_service.set_result("data.csv", MockDataResult(success=True, data=[]))
        executor = DataExecutor(runtime)

        node = DataNode("data", "data.csv", "csv")
        node.transforms = [
            MockTransformNode([FilterNode("age > 18")])
        ]

        executor.execute(node, runtime.execution_context)

        params = runtime._data_import_service.last_params
        assert len(params["transforms"]) == 1
        assert params["transforms"][0]["type"] == "filter"
        assert params["transforms"][0]["condition"] == "age > 18"

    def test_sort_transform(self):
        """Test sort transformation"""
        runtime = MockDataRuntime()
        runtime._data_import_service.set_result("data.csv", MockDataResult(success=True, data=[]))
        executor = DataExecutor(runtime)

        node = DataNode("data", "data.csv", "csv")
        node.transforms = [
            MockTransformNode([SortNode("name", "desc")])
        ]

        executor.execute(node, runtime.execution_context)

        params = runtime._data_import_service.last_params
        assert params["transforms"][0]["by"] == "name"
        assert params["transforms"][0]["order"] == "desc"

    def test_limit_transform(self):
        """Test limit transformation"""
        runtime = MockDataRuntime()
        runtime._data_import_service.set_result("data.csv", MockDataResult(success=True, data=[]))
        executor = DataExecutor(runtime)

        node = DataNode("data", "data.csv", "csv")
        node.transforms = [
            MockTransformNode([LimitNode(100)])
        ]

        executor.execute(node, runtime.execution_context)

        params = runtime._data_import_service.last_params
        assert params["transforms"][0]["value"] == 100

    def test_compute_transform(self):
        """Test compute transformation"""
        runtime = MockDataRuntime()
        runtime._data_import_service.set_result("data.csv", MockDataResult(success=True, data=[]))
        executor = DataExecutor(runtime)

        node = DataNode("data", "data.csv", "csv")
        node.transforms = [
            MockTransformNode([ComputeNode("fullName", "firstName + ' ' + lastName", "string")])
        ]

        executor.execute(node, runtime.execution_context)

        params = runtime._data_import_service.last_params
        assert params["transforms"][0]["field"] == "fullName"
        assert params["transforms"][0]["expression"] == "firstName + ' ' + lastName"


class TestResultStorage:
    """Test result storage"""

    def test_stores_data_array(self):
        """Test that data array is stored"""
        runtime = MockDataRuntime()
        runtime._data_import_service.set_result("data.csv", MockDataResult(
            success=True,
            data=[{"a": 1}, {"a": 2}],
            recordCount=2
        ))
        executor = DataExecutor(runtime)

        node = DataNode("myData", "data.csv", "csv")

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("myData")
        assert isinstance(stored, list)
        assert len(stored) == 2

    def test_stores_result_metadata(self):
        """Test that result metadata is stored"""
        runtime = MockDataRuntime()
        runtime._data_import_service.set_result("data.csv", MockDataResult(
            success=True,
            data=[{"a": 1}],
            recordCount=1,
            loadTime=50,
            cached=False,
            source="data.csv"
        ))
        executor = DataExecutor(runtime)

        node = DataNode("myData", "data.csv", "csv")

        executor.execute(node, runtime.execution_context)

        metadata = runtime.execution_context.get_variable("myData_result")
        assert metadata["success"] is True
        assert metadata["recordCount"] == 1
        assert metadata["loadTime"] == 50
        assert metadata["source"] == "data.csv"

    def test_custom_result_variable(self):
        """Test storing in custom result variable"""
        runtime = MockDataRuntime()
        runtime._data_import_service.set_result("data.csv", MockDataResult(success=True, data=[]))
        executor = DataExecutor(runtime)

        node = DataNode("data", "data.csv", "csv")
        node.result = "customMeta"

        executor.execute(node, runtime.execution_context)

        custom = runtime.execution_context.get_variable("customMeta")
        assert custom["success"] is True


class TestDatabinding:
    """Test databinding in data import"""

    def test_source_databinding(self):
        """Test source path can use databinding"""
        runtime = MockDataRuntime({"fileName": "users.csv"})
        runtime._data_import_service.set_result("users.csv", MockDataResult(success=True, data=[]))
        executor = DataExecutor(runtime)

        node = DataNode("data", "{fileName}", "csv")

        executor.execute(node, runtime.execution_context)

        assert runtime._data_import_service.last_source == "users.csv"


class TestErrorHandling:
    """Test error handling"""

    def test_import_error_raises_executor_error(self):
        """Test that import error raises ExecutorError"""
        runtime = MockDataRuntime()
        runtime._data_import_service.import_data = MagicMock(side_effect=Exception("Import failed"))
        executor = DataExecutor(runtime)

        node = DataNode("data", "invalid.csv", "csv")

        with pytest.raises(ExecutorError, match="Data import error in 'data'"):
            executor.execute(node, runtime.execution_context)
