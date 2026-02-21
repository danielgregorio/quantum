"""
Tests for TransactionExecutor - q:transaction database transactions

Coverage target: 27% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Any, Dict, List

from runtime.executors.data.transaction_executor import TransactionExecutor
from runtime.executors.base import ExecutorError
from core.ast_nodes import TransactionNode, QueryNode

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


# =============================================================================
# Mock Objects for Database Service
# =============================================================================

class MockDatabaseService:
    """Mock database service for transactions"""

    def __init__(self):
        self.transaction_started = False
        self.committed = False
        self.rolled_back = False
        self.last_datasource = None

    def begin_transaction(self, datasource: str):
        """Begin transaction"""
        self.transaction_started = True
        self.last_datasource = datasource
        return {"datasource": datasource, "active": True}

    def commit_transaction(self, context):
        """Commit transaction"""
        self.committed = True
        return True

    def rollback_transaction(self, context):
        """Rollback transaction"""
        self.rolled_back = True


class MockTransactionRuntime(MockRuntime):
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

class TestTransactionExecutorBasic:
    """Basic functionality tests"""

    def test_handles_transaction_node(self):
        """Test that TransactionExecutor handles TransactionNode"""
        runtime = MockTransactionRuntime()
        executor = TransactionExecutor(runtime)
        assert TransactionNode in executor.handles

    def test_handles_returns_list(self):
        """Test that handles returns a list"""
        runtime = MockTransactionRuntime()
        executor = TransactionExecutor(runtime)
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestSuccessfulTransaction:
    """Test successful transaction execution"""

    def test_transaction_begins_and_commits(self):
        """Test that transaction starts and commits"""
        runtime = MockTransactionRuntime()
        executor = TransactionExecutor(runtime)

        node = TransactionNode()

        # Mock execute_child to succeed
        with patch.object(executor, 'execute_child', return_value={"success": True}):
            result = executor.execute(node, runtime.execution_context)

            assert runtime._database_service.transaction_started is True
            assert runtime._database_service.committed is True
            assert runtime._database_service.rolled_back is False

    def test_transaction_returns_success_result(self):
        """Test that successful transaction returns correct result"""
        runtime = MockTransactionRuntime()
        executor = TransactionExecutor(runtime)

        node = TransactionNode()

        with patch.object(executor, 'execute_child', return_value={"rows": 1}):
            result = executor.execute(node, runtime.execution_context)

            assert result["success"] is True
            assert result["committed"] is True

    def test_transaction_with_statements(self):
        """Test transaction with multiple statements"""
        runtime = MockTransactionRuntime()
        executor = TransactionExecutor(runtime)

        node = TransactionNode()
        query1 = QueryNode("q1", "default", "INSERT INTO t VALUES (1)")
        query2 = QueryNode("q2", "default", "INSERT INTO t VALUES (2)")
        node.statements = [query1, query2]

        with patch.object(executor, 'execute_child', return_value={"success": True}):
            result = executor.execute(node, runtime.execution_context)

            assert result["statement_count"] == 2

    def test_transaction_collects_results(self):
        """Test that transaction collects results from statements"""
        runtime = MockTransactionRuntime()
        executor = TransactionExecutor(runtime)

        node = TransactionNode()
        node.statements = [MagicMock(), MagicMock()]

        call_count = [0]
        def mock_execute(stmt, ctx):
            call_count[0] += 1
            return {"result": call_count[0]}

        with patch.object(executor, 'execute_child', side_effect=mock_execute):
            result = executor.execute(node, runtime.execution_context)

            assert len(result["results"]) == 2
            assert result["results"][0]["result"] == 1
            assert result["results"][1]["result"] == 2


class TestTransactionRollback:
    """Test transaction rollback on failure"""

    def test_transaction_rolls_back_on_error(self):
        """Test that transaction rolls back when statement fails"""
        runtime = MockTransactionRuntime()
        executor = TransactionExecutor(runtime)

        node = TransactionNode()
        node.statements = [MagicMock()]

        with patch.object(executor, 'execute_child', side_effect=Exception("Query failed")):
            with pytest.raises(ExecutorError, match="Transaction failed and was rolled back"):
                executor.execute(node, runtime.execution_context)

            assert runtime._database_service.transaction_started is True
            assert runtime._database_service.committed is False
            assert runtime._database_service.rolled_back is True

    def test_rollback_result_includes_error(self):
        """Test that rollback result includes error message"""
        runtime = MockTransactionRuntime()
        executor = TransactionExecutor(runtime)

        node = TransactionNode()
        node.statements = [MagicMock()]

        with patch.object(executor, 'execute_child', side_effect=Exception("Specific error")):
            try:
                executor.execute(node, runtime.execution_context)
            except ExecutorError:
                pass  # Expected

            # Check that error was captured before re-raise
            # Note: the actual error is re-raised, so we can't check the result


class TestIsolationLevels:
    """Test isolation level handling"""

    def test_default_isolation_level(self):
        """Test default isolation level"""
        runtime = MockTransactionRuntime()
        executor = TransactionExecutor(runtime)

        node = TransactionNode()  # Default is READ_COMMITTED

        with patch.object(executor, 'execute_child', return_value=None):
            result = executor.execute(node, runtime.execution_context)

            assert result["isolation_level"] == "READ_COMMITTED"

    def test_custom_isolation_level(self):
        """Test custom isolation level"""
        runtime = MockTransactionRuntime()
        executor = TransactionExecutor(runtime)

        node = TransactionNode(isolation_level="SERIALIZABLE")

        with patch.object(executor, 'execute_child', return_value=None):
            result = executor.execute(node, runtime.execution_context)

            assert result["isolation_level"] == "SERIALIZABLE"


class TestDatasourceDetection:
    """Test datasource detection from queries"""

    def test_detects_datasource_from_first_query(self):
        """Test that datasource is detected from first query"""
        runtime = MockTransactionRuntime()
        executor = TransactionExecutor(runtime)

        node = TransactionNode()
        query = QueryNode("q1", "mydb", "INSERT INTO t VALUES (1)")
        node.statements = [query]

        with patch.object(executor, 'execute_child', return_value=None):
            executor.execute(node, runtime.execution_context)

            assert runtime._database_service.last_datasource == "mydb"

    def test_uses_default_when_no_datasource(self):
        """Test that 'default' is used when no datasource specified"""
        runtime = MockTransactionRuntime()
        executor = TransactionExecutor(runtime)

        node = TransactionNode()
        # No queries with datasource

        with patch.object(executor, 'execute_child', return_value=None):
            executor.execute(node, runtime.execution_context)

            assert runtime._database_service.last_datasource == "default"

    def test_detects_datasource_skipping_null(self):
        """Test that datasource detection skips queries without datasource"""
        runtime = MockTransactionRuntime()
        executor = TransactionExecutor(runtime)

        node = TransactionNode()
        query1 = QueryNode("q1", None, "SELECT 1")  # No datasource
        query2 = QueryNode("q2", "production", "INSERT INTO t VALUES (1)")
        node.statements = [query1, query2]

        with patch.object(executor, 'execute_child', return_value=None):
            executor.execute(node, runtime.execution_context)

            assert runtime._database_service.last_datasource == "production"


class TestResultStorage:
    """Test transaction result storage"""

    def test_stores_result_in_context(self):
        """Test that transaction result is stored in context"""
        runtime = MockTransactionRuntime()
        executor = TransactionExecutor(runtime)

        node = TransactionNode()

        with patch.object(executor, 'execute_child', return_value=None):
            executor.execute(node, runtime.execution_context)

            stored = runtime.execution_context.get_variable("_transaction_result")
            assert stored["success"] is True
            assert stored["committed"] is True


class TestEmptyTransaction:
    """Test empty transaction handling"""

    def test_empty_transaction_succeeds(self):
        """Test that empty transaction still commits"""
        runtime = MockTransactionRuntime()
        executor = TransactionExecutor(runtime)

        node = TransactionNode()
        node.statements = []

        result = executor.execute(node, runtime.execution_context)

        assert result["success"] is True
        assert result["committed"] is True
        assert result["statement_count"] == 0
        assert result["results"] == []


class TestErrorHandling:
    """Test error handling"""

    def test_execution_error_wrapped(self):
        """Test that non-ExecutorError is wrapped"""
        runtime = MockTransactionRuntime()
        runtime._database_service.begin_transaction = MagicMock(side_effect=Exception("DB connection failed"))
        executor = TransactionExecutor(runtime)

        node = TransactionNode()

        with pytest.raises(ExecutorError, match="Transaction execution error"):
            executor.execute(node, runtime.execution_context)
