"""
Tests for QueryExecutor - q:query database execution

Coverage target: 15% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Any, Dict, List

from runtime.executors.data.query_executor import QueryExecutor
from runtime.executors.base import ExecutorError
from core.ast_nodes import QueryNode, QueryParamNode

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


# =============================================================================
# Mock Objects for Database Service
# =============================================================================

@dataclass
class MockQueryResult:
    """Mock query result"""
    success: bool = True
    data: List[Dict[str, Any]] = None
    record_count: int = 0
    column_list: List[str] = None
    execution_time: int = 0
    sql: str = ""

    def __post_init__(self):
        if self.data is None:
            self.data = []
        if self.column_list is None:
            self.column_list = []

    def to_dict(self):
        return {
            'success': self.success,
            'data': self.data,
            'recordCount': self.record_count,
            'columnList': self.column_list,
            'executionTime': self.execution_time,
            'sql': self.sql
        }


class MockDatabaseService:
    """Mock database service"""

    def __init__(self):
        self.last_query = None
        self.last_params = None
        self._results = {}

    def set_result(self, datasource: str, result: MockQueryResult):
        """Set mock result for a datasource"""
        self._results[datasource] = result

    def execute_query(self, datasource: str, sql: str, params: Dict[str, Any] = None) -> MockQueryResult:
        """Execute mock query"""
        self.last_query = sql
        self.last_params = params

        if datasource in self._results:
            return self._results[datasource]

        # Default empty result
        return MockQueryResult(success=True, data=[], record_count=0)

    def begin_transaction(self, datasource: str):
        return {"datasource": datasource, "active": True}

    def commit_transaction(self, context):
        return True

    def rollback_transaction(self, context):
        pass


class MockQueryRuntime(MockRuntime):
    """Extended mock runtime with database service"""

    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._database_service = MockDatabaseService()
        self._services = MagicMock()
        self._services.database = self._database_service

    @property
    def services(self):
        return self._services


# =============================================================================
# Test Classes
# =============================================================================

class TestQueryExecutorBasic:
    """Basic functionality tests"""

    def test_handles_query_node(self):
        """Test that QueryExecutor handles QueryNode"""
        runtime = MockQueryRuntime()
        executor = QueryExecutor(runtime)
        assert QueryNode in executor.handles

    def test_handles_returns_list(self):
        """Test that handles returns a list"""
        runtime = MockQueryRuntime()
        executor = QueryExecutor(runtime)
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestSimpleQuery:
    """Test simple query execution"""

    def test_execute_simple_query(self):
        """Test executing a simple SELECT query"""
        runtime = MockQueryRuntime()
        runtime._database_service.set_result("default", MockQueryResult(
            success=True,
            data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
            record_count=2,
            column_list=["id", "name"]
        ))
        executor = QueryExecutor(runtime)

        node = QueryNode("users", "default", "SELECT * FROM users")

        result = executor.execute(node, runtime.execution_context)

        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0]["name"] == "Alice"

    def test_query_stores_result_in_context(self):
        """Test that query result is stored in context"""
        runtime = MockQueryRuntime()
        runtime._database_service.set_result("default", MockQueryResult(
            success=True,
            data=[{"id": 1, "name": "Test"}],
            record_count=1
        ))
        executor = QueryExecutor(runtime)

        node = QueryNode("myQuery", "default", "SELECT * FROM test")

        executor.execute(node, runtime.execution_context)

        # Result should be stored as array
        stored = runtime.execution_context.get_variable("myQuery")
        assert isinstance(stored, list)
        assert len(stored) == 1

    def test_query_stores_metadata(self):
        """Test that query metadata is stored"""
        runtime = MockQueryRuntime()
        runtime._database_service.set_result("default", MockQueryResult(
            success=True,
            data=[{"value": 42}],
            record_count=1
        ))
        executor = QueryExecutor(runtime)

        node = QueryNode("result", "default", "SELECT 42 as value")

        executor.execute(node, runtime.execution_context)

        # Metadata should be stored with _result suffix
        metadata = runtime.execution_context.get_variable("result_result")
        assert metadata["success"] is True


class TestQueryParameters:
    """Test query parameter handling"""

    def test_query_with_string_param(self):
        """Test query with string parameter"""
        runtime = MockQueryRuntime({"searchName": "Alice"})
        runtime._database_service.set_result("default", MockQueryResult(
            success=True,
            data=[{"id": 1, "name": "Alice"}],
            record_count=1
        ))
        executor = QueryExecutor(runtime)

        node = QueryNode("users", "default", "SELECT * FROM users WHERE name = :name")
        param = QueryParamNode("name", "{searchName}", "string")
        node.params.append(param)

        # Mock the query validator
        with patch('runtime.query_validators.QueryValidator') as MockValidator:
            MockValidator.validate_param.return_value = "Alice"
            MockValidator.sanitize_sql.return_value = None

            result = executor.execute(node, runtime.execution_context)

            assert result.success is True
            MockValidator.validate_param.assert_called()

    def test_query_with_integer_param(self):
        """Test query with integer parameter"""
        runtime = MockQueryRuntime({"userId": 42})
        runtime._database_service.set_result("default", MockQueryResult(
            success=True,
            data=[{"id": 42, "name": "Test"}],
            record_count=1
        ))
        executor = QueryExecutor(runtime)

        node = QueryNode("user", "default", "SELECT * FROM users WHERE id = :id")
        param = QueryParamNode("id", "{userId}", "integer")
        node.params.append(param)

        with patch('runtime.query_validators.QueryValidator') as MockValidator:
            MockValidator.validate_param.return_value = 42
            MockValidator.sanitize_sql.return_value = None

            result = executor.execute(node, runtime.execution_context)

            assert result.success is True

    def test_query_param_validation_error(self):
        """Test that invalid parameter raises error"""
        runtime = MockQueryRuntime({"value": "not_a_number"})
        executor = QueryExecutor(runtime)

        node = QueryNode("test", "default", "SELECT * FROM t WHERE id = :id")
        param = QueryParamNode("id", "{value}", "integer")
        node.params.append(param)

        with patch('runtime.query_validators.QueryValidator') as MockValidator:
            from runtime.query_validators import QueryValidationError
            MockValidator.validate_param.side_effect = QueryValidationError("Invalid integer")

            with pytest.raises(ExecutorError, match="Parameter 'id' validation failed"):
                executor.execute(node, runtime.execution_context)


class TestQueryPagination:
    """Test query pagination"""

    def test_pagination_generates_count_query(self):
        """Test that pagination generates COUNT query"""
        runtime = MockQueryRuntime()

        # First call for count, second for actual data
        call_count = [0]
        def mock_execute(datasource, sql, params):
            call_count[0] += 1
            if 'COUNT' in sql:
                return MockQueryResult(success=True, data=[{"count": 100}])
            return MockQueryResult(success=True, data=[{"id": 1}], record_count=1)

        runtime._database_service.execute_query = mock_execute
        executor = QueryExecutor(runtime)

        node = QueryNode("users", "default", "SELECT * FROM users ORDER BY id")
        node.paginate = True
        node.page = 1
        node.page_size = 10

        with patch('runtime.query_validators.QueryValidator') as MockValidator:
            MockValidator.sanitize_sql.return_value = None

            result = executor.execute(node, runtime.execution_context)

            assert call_count[0] == 2  # COUNT + SELECT

    def test_pagination_adds_limit_offset(self):
        """Test that pagination adds LIMIT and OFFSET"""
        runtime = MockQueryRuntime()
        captured_sql = []

        def mock_execute(datasource, sql, params):
            captured_sql.append(sql)
            if 'COUNT' in sql:
                return MockQueryResult(success=True, data=[{"count": 100}])
            return MockQueryResult(success=True, data=[], record_count=0)

        runtime._database_service.execute_query = mock_execute
        executor = QueryExecutor(runtime)

        node = QueryNode("users", "default", "SELECT * FROM users")
        node.paginate = True
        node.page = 3
        node.page_size = 20

        with patch('runtime.query_validators.QueryValidator') as MockValidator:
            MockValidator.sanitize_sql.return_value = None

            executor.execute(node, runtime.execution_context)

            # Second SQL should have LIMIT and OFFSET
            assert "LIMIT 20" in captured_sql[1]
            assert "OFFSET 40" in captured_sql[1]

    def test_pagination_metadata(self):
        """Test pagination metadata is calculated correctly"""
        runtime = MockQueryRuntime()

        def mock_execute(datasource, sql, params):
            if 'COUNT' in sql:
                return MockQueryResult(success=True, data=[{"count": 95}])
            return MockQueryResult(success=True, data=[{"id": i} for i in range(10)])

        runtime._database_service.execute_query = mock_execute
        executor = QueryExecutor(runtime)

        node = QueryNode("items", "default", "SELECT * FROM items")
        node.paginate = True
        node.page = 2
        node.page_size = 10

        with patch('runtime.query_validators.QueryValidator') as MockValidator:
            MockValidator.sanitize_sql.return_value = None

            executor.execute(node, runtime.execution_context)

            metadata = runtime.execution_context.get_variable("items_result")
            pagination = metadata["pagination"]

            assert pagination["totalRecords"] == 95
            assert pagination["totalPages"] == 10  # ceil(95/10)
            assert pagination["currentPage"] == 2
            assert pagination["hasNextPage"] is True
            assert pagination["hasPreviousPage"] is True


class TestQueryOfQueries:
    """Test Query of Queries (in-memory SQL)"""

    def test_qoq_basic_select(self):
        """Test basic Query of Queries SELECT"""
        runtime = MockQueryRuntime({
            "sourceData": [
                {"id": 1, "name": "Alice", "age": 30},
                {"id": 2, "name": "Bob", "age": 25},
                {"id": 3, "name": "Charlie", "age": 35}
            ]
        })
        executor = QueryExecutor(runtime)

        node = QueryNode("filtered", None, "SELECT * FROM sourceData WHERE age > 28")
        node.source = "sourceData"

        result = executor.execute(node, runtime.execution_context)

        assert result.success is True
        assert result.record_count == 2  # Alice and Charlie

    def test_qoq_with_ordering(self):
        """Test Query of Queries with ORDER BY"""
        runtime = MockQueryRuntime({
            "data": [
                {"value": 30},
                {"value": 10},
                {"value": 20}
            ]
        })
        executor = QueryExecutor(runtime)

        node = QueryNode("sorted", None, "SELECT * FROM data ORDER BY value ASC")
        node.source = "data"

        result = executor.execute(node, runtime.execution_context)

        assert result.success is True
        # SQLite stores as TEXT, so values are strings
        assert str(result.data[0]["value"]) == "10"
        assert str(result.data[2]["value"]) == "30"

    def test_qoq_empty_source(self):
        """Test Query of Queries with empty source"""
        runtime = MockQueryRuntime({"emptyData": []})
        executor = QueryExecutor(runtime)

        node = QueryNode("result", None, "SELECT * FROM emptyData")
        node.source = "emptyData"

        result = executor.execute(node, runtime.execution_context)

        assert result.success is True
        assert result.data == []
        assert result.record_count == 0

    def test_qoq_source_not_found_raises_error(self):
        """Test that missing source raises error"""
        runtime = MockQueryRuntime({})
        executor = QueryExecutor(runtime)

        node = QueryNode("result", None, "SELECT * FROM nonexistent")
        node.source = "nonexistent"

        with pytest.raises(ExecutorError, match="Query execution error"):
            executor.execute(node, runtime.execution_context)

    def test_qoq_invalid_source_type_raises_error(self):
        """Test that non-list source raises error"""
        runtime = MockQueryRuntime({"notAList": "string value"})
        executor = QueryExecutor(runtime)

        node = QueryNode("result", None, "SELECT * FROM notAList")
        node.source = "notAList"

        with pytest.raises(ExecutorError, match="is not a query result"):
            executor.execute(node, runtime.execution_context)


class TestKnowledgeQuery:
    """Test knowledge base queries (RAG)"""

    def test_knowledge_query_delegates_to_runtime(self):
        """Test that knowledge query delegates to runtime"""
        runtime = MockQueryRuntime()
        runtime._execute_knowledge_query = MagicMock(return_value={"results": []})
        executor = QueryExecutor(runtime)

        node = QueryNode("kb_result", "knowledge:docs", "Find relevant documents")

        with patch('runtime.query_validators.QueryValidator') as MockValidator:
            MockValidator.validate_param.return_value = None

            executor.execute(node, runtime.execution_context)

            runtime._execute_knowledge_query.assert_called_once()


class TestSingleRowFieldExposure:
    """Test single-row field exposure"""

    def test_single_row_exposes_fields(self):
        """Test that single row results expose fields directly"""
        runtime = MockQueryRuntime()
        runtime._database_service.set_result("default", MockQueryResult(
            success=True,
            data=[{"id": 1, "name": "Alice", "email": "alice@example.com"}],
            record_count=1
        ))
        executor = QueryExecutor(runtime)

        node = QueryNode("user", "default", "SELECT * FROM users WHERE id = 1")

        with patch('runtime.query_validators.QueryValidator') as MockValidator:
            MockValidator.sanitize_sql.return_value = None

            executor.execute(node, runtime.execution_context)

            # Fields should be accessible as user.fieldname
            assert runtime.execution_context.get_variable("user.id") == 1
            assert runtime.execution_context.get_variable("user.name") == "Alice"
            assert runtime.execution_context.get_variable("user.email") == "alice@example.com"

    def test_multiple_rows_dont_expose_fields(self):
        """Test that multiple row results don't expose individual fields"""
        runtime = MockQueryRuntime()
        runtime._database_service.set_result("default", MockQueryResult(
            success=True,
            data=[{"id": 1}, {"id": 2}],
            record_count=2
        ))
        executor = QueryExecutor(runtime)

        node = QueryNode("users", "default", "SELECT * FROM users")

        with patch('runtime.query_validators.QueryValidator') as MockValidator:
            MockValidator.sanitize_sql.return_value = None

            executor.execute(node, runtime.execution_context)

            # Fields should not be exposed for multiple rows
            with pytest.raises(KeyError):
                runtime.execution_context.get_variable("users.id")


class TestCountQueryGeneration:
    """Test COUNT query generation"""

    def test_generates_count_query(self):
        """Test count query generation"""
        runtime = MockQueryRuntime()
        executor = QueryExecutor(runtime)

        original_sql = "SELECT id, name FROM users WHERE active = 1 ORDER BY name"
        count_sql = executor._generate_count_query(original_sql)

        assert "COUNT(*)" in count_sql
        assert "ORDER BY" not in count_sql

    def test_removes_limit_offset(self):
        """Test that LIMIT and OFFSET are removed from count query"""
        runtime = MockQueryRuntime()
        executor = QueryExecutor(runtime)

        original_sql = "SELECT * FROM items LIMIT 10 OFFSET 20"
        count_sql = executor._generate_count_query(original_sql)

        assert "LIMIT" not in count_sql
        assert "OFFSET" not in count_sql


class TestErrorHandling:
    """Test error handling"""

    def test_execution_error_includes_query_name(self):
        """Test that execution error includes query name"""
        runtime = MockQueryRuntime()
        runtime._database_service.execute_query = MagicMock(side_effect=Exception("DB error"))
        executor = QueryExecutor(runtime)

        node = QueryNode("myQuery", "default", "SELECT * FROM fail")

        with patch('runtime.query_validators.QueryValidator') as MockValidator:
            MockValidator.sanitize_sql.return_value = None

            with pytest.raises(ExecutorError, match="Query execution error in 'myQuery'"):
                executor.execute(node, runtime.execution_context)

    def test_qoq_sql_error_raises_executor_error(self):
        """Test that QoQ SQL error raises ExecutorError"""
        runtime = MockQueryRuntime({
            "data": [{"id": 1}]
        })
        executor = QueryExecutor(runtime)

        node = QueryNode("result", None, "INVALID SQL SYNTAX!!!")
        node.source = "data"

        with pytest.raises(ExecutorError, match="Query of Queries SQL error"):
            executor.execute(node, runtime.execution_context)


class TestResultVariable:
    """Test result variable storage"""

    def test_custom_result_variable(self):
        """Test storing result in custom variable"""
        runtime = MockQueryRuntime()
        runtime._database_service.set_result("default", MockQueryResult(
            success=True,
            data=[{"count": 5}],
            record_count=1
        ))
        executor = QueryExecutor(runtime)

        node = QueryNode("query", "default", "SELECT COUNT(*) as count FROM t")
        node.result = "customResult"

        with patch('runtime.query_validators.QueryValidator') as MockValidator:
            MockValidator.sanitize_sql.return_value = None

            executor.execute(node, runtime.execution_context)

            # Should be stored in custom variable
            custom = runtime.execution_context.get_variable("customResult")
            assert custom["success"] is True
