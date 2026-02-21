"""
Query Executor - Execute q:query statements

Handles database queries with parameter validation, pagination, and Query of Queries.
"""

from typing import Any, List, Dict, Type
import sqlite3
import time
import re
from runtime.executors.base import BaseExecutor, ExecutorError
from core.ast_nodes import QueryNode


class QueryExecutor(BaseExecutor):
    """
    Executor for q:query statements.

    Supports:
    - Database queries with parameterized SQL
    - Pagination with automatic COUNT
    - Query of Queries (in-memory SQL on result sets)
    - Knowledge base queries (virtual datasource)
    """

    @property
    def handles(self) -> List[Type]:
        return [QueryNode]

    def execute(self, node: QueryNode, exec_context) -> Any:
        """
        Execute database query.

        Args:
            node: QueryNode with query configuration
            exec_context: Execution context

        Returns:
            QueryResult with data and metadata
        """
        try:
            context = exec_context.get_all_variables()

            # Resolve and validate parameters
            resolved_params = self._resolve_params(node, context)

            # Check for knowledge base query
            if node.datasource and node.datasource.startswith('knowledge:'):
                return self._execute_knowledge_query(node, resolved_params, exec_context)

            # Check for Query of Queries
            if node.source:
                return self._execute_query_of_queries(node, context, resolved_params, exec_context)

            # Execute standard database query
            return self._execute_database_query(node, resolved_params, exec_context)

        except Exception as e:
            raise ExecutorError(f"Query execution error in '{node.name}': {e}")

    def _resolve_params(self, node: QueryNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve and validate query parameters"""
        from runtime.query_validators import QueryValidator, QueryValidationError

        resolved_params = {}
        for param_node in node.params:
            param_value = self.apply_databinding(param_node.value, context)

            attributes = {
                'null': param_node.null,
                'max_length': param_node.max_length,
                'scale': param_node.scale
            }

            try:
                validated_value = QueryValidator.validate_param(
                    param_value,
                    param_node.param_type,
                    attributes
                )
                resolved_params[param_node.name] = validated_value
            except QueryValidationError as e:
                raise ExecutorError(f"Parameter '{param_node.name}' validation failed: {e}")

        return resolved_params

    def _execute_database_query(self, node: QueryNode, params: Dict[str, Any], exec_context) -> Any:
        """Execute standard database query"""
        from runtime.query_validators import QueryValidator

        # Sanitize SQL
        QueryValidator.sanitize_sql(node.sql)

        # Handle pagination
        pagination_metadata = None
        sql_to_execute = node.sql

        if node.paginate:
            pagination_metadata, sql_to_execute = self._handle_pagination(node, params)

        # Execute query
        result = self.services.database.execute_query(
            node.datasource,
            sql_to_execute,
            params
        )

        # Store results
        self._store_query_result(node, result, pagination_metadata, exec_context)

        return result

    def _handle_pagination(self, node: QueryNode, params: Dict[str, Any]):
        """Handle query pagination"""
        count_sql = self._generate_count_query(node.sql)
        count_result = self.services.database.execute_query(
            node.datasource,
            count_sql,
            params
        )

        total_records = count_result.data[0]['count'] if count_result.data else 0

        page = node.page if node.page is not None else 1
        page_size = node.page_size
        total_pages = (total_records + page_size - 1) // page_size

        offset = (page - 1) * page_size
        sql_to_execute = f"{node.sql}\nLIMIT {page_size} OFFSET {offset}"

        pagination_metadata = {
            'totalRecords': total_records,
            'totalPages': total_pages,
            'currentPage': page,
            'pageSize': page_size,
            'hasNextPage': page < total_pages,
            'hasPreviousPage': page > 1,
            'startRecord': offset + 1 if total_records > 0 else 0,
            'endRecord': min(offset + page_size, total_records)
        }

        return pagination_metadata, sql_to_execute

    def _generate_count_query(self, original_sql: str) -> str:
        """Generate COUNT(*) query from original SQL"""
        sql = ' '.join(original_sql.split())
        sql = re.sub(r'\s+ORDER\s+BY\s+[^;]+?(?=\s+(?:LIMIT|OFFSET|FOR\s+UPDATE)|$)', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\s+LIMIT\s+\d+', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\s+OFFSET\s+\d+', '', sql, flags=re.IGNORECASE)
        return f"SELECT COUNT(*) as count FROM ({sql}) AS count_query"

    def _execute_query_of_queries(self, node: QueryNode, context: Dict[str, Any],
                                   params: Dict[str, Any], exec_context) -> Any:
        """Execute Query of Queries - SQL on in-memory result sets"""
        from runtime.database_service import QueryResult

        source_name = node.source
        source_data = context.get(source_name) or exec_context.get_variable(source_name)

        if source_data is None:
            raise ExecutorError(f"Source query '{source_name}' not found")

        if not isinstance(source_data, list):
            raise ExecutorError(f"Source '{source_name}' is not a query result")

        if not source_data:
            result = QueryResult(
                success=True, data=[], record_count=0,
                column_list=[], execution_time=0, sql=node.sql
            )
            self._store_query_result(node, result, None, exec_context)
            return result

        # Create in-memory SQLite database
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            first_row = source_data[0]
            if not isinstance(first_row, dict):
                raise ExecutorError("Source data must be list of dictionaries")

            columns = list(first_row.keys())
            column_defs = ', '.join([f'"{col}" TEXT' for col in columns])
            cursor.execute(f'CREATE TABLE source_table ({column_defs})')

            placeholders = ', '.join(['?' for _ in columns])
            for row in source_data:
                values = [row.get(col) for col in columns]
                cursor.execute(f'INSERT INTO source_table VALUES ({placeholders})', values)

            sql = node.sql.replace(f'FROM {source_name}', 'FROM source_table')
            sql = sql.replace(f'FROM {{{source_name}}}', 'FROM source_table')

            for param_name in params:
                sql = sql.replace(f':{param_name}', '?')

            start_time = time.time()
            cursor.execute(sql, list(params.values()) if params else [])
            result_rows = cursor.fetchall()
            execution_time = (time.time() - start_time) * 1000

            result_data = []
            column_names = []
            if result_rows:
                column_names = [desc[0] for desc in cursor.description]
                for row in result_rows:
                    result_data.append(dict(zip(column_names, row)))

            conn.close()

            result = QueryResult(
                success=True,
                data=result_data,
                record_count=len(result_data),
                column_list=column_names,
                execution_time=int(execution_time),
                sql=node.sql
            )

            self._store_query_result(node, result, None, exec_context)
            return result

        except sqlite3.Error as e:
            conn.close()
            raise ExecutorError(f"Query of Queries SQL error: {e}")

    def _execute_knowledge_query(self, node: QueryNode, params: Dict[str, Any], exec_context) -> Any:
        """Execute knowledge base query (RAG)"""
        # Delegate to runtime's knowledge query handler
        return self.runtime._execute_knowledge_query(node, params, exec_context)

    def _store_query_result(self, node: QueryNode, result, pagination_metadata, exec_context):
        """Store query result in context"""
        result_dict = result.to_dict()

        if pagination_metadata:
            result_dict['pagination'] = pagination_metadata

        # Store data as array
        exec_context.set_variable(node.name, result.data, scope="component")

        # Store full result with metadata
        exec_context.set_variable(f"{node.name}_result", result_dict, scope="component")

        # Single-row field exposure
        if result.data and len(result.data) == 1 and isinstance(result.data[0], dict):
            for field_name, field_value in result.data[0].items():
                dotted_key = f"{node.name}.{field_name}"
                exec_context.set_variable(dotted_key, field_value, scope="component")

        if node.result:
            exec_context.set_variable(node.result, result_dict, scope="component")
