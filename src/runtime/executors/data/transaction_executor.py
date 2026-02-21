"""
Transaction Executor - Execute q:transaction statements

Handles database transactions with atomic commit/rollback.
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError
from core.ast_nodes import TransactionNode, QueryNode


class TransactionExecutor(BaseExecutor):
    """
    Executor for q:transaction statements.

    Supports:
    - Atomic transaction execution
    - Automatic rollback on failure
    - Multiple isolation levels
    - Nested statement execution
    """

    @property
    def handles(self) -> List[Type]:
        return [TransactionNode]

    def execute(self, node: TransactionNode, exec_context) -> Any:
        """
        Execute database transaction.

        Args:
            node: TransactionNode with statements to execute
            exec_context: Execution context

        Returns:
            Transaction result dict with success status
        """
        try:
            # Determine datasource
            datasource_name = self._get_datasource(node)

            # Begin transaction
            transaction_context = self.services.database.begin_transaction(datasource_name)

            results = []
            try:
                # Execute all statements
                for statement in node.statements:
                    result = self.execute_child(statement, exec_context)
                    results.append(result)

                # Commit transaction
                success = self.services.database.commit_transaction(transaction_context)

                transaction_result = {
                    'success': success,
                    'committed': True,
                    'isolation_level': node.isolation_level,
                    'statement_count': len(node.statements),
                    'results': results
                }

            except Exception as stmt_error:
                # Rollback on failure
                self.services.database.rollback_transaction(transaction_context)

                transaction_result = {
                    'success': False,
                    'rolled_back': True,
                    'error': str(stmt_error),
                    'isolation_level': node.isolation_level
                }

                raise ExecutorError(f"Transaction failed and was rolled back: {stmt_error}")

            # Store result
            exec_context.set_variable('_transaction_result', transaction_result, scope="component")

            return transaction_result

        except ExecutorError:
            raise
        except Exception as e:
            raise ExecutorError(f"Transaction execution error: {e}")

    def _get_datasource(self, node: TransactionNode) -> str:
        """Get datasource from first query in transaction"""
        for stmt in node.statements:
            if isinstance(stmt, QueryNode) and stmt.datasource:
                return stmt.datasource
        return "default"
