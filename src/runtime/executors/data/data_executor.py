"""
Data Executor - Execute q:data statements

Handles data import from CSV, JSON, XML sources with transformations.
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError
from core.ast_nodes import DataNode


class DataExecutor(BaseExecutor):
    """
    Executor for q:data statements.

    Supports:
    - CSV import with column definitions
    - JSON import from files or URLs
    - XML import with XPath
    - Data transformations (filter, sort, limit, compute)
    - Response caching with TTL
    """

    @property
    def handles(self) -> List[Type]:
        return [DataNode]

    def execute(self, node: DataNode, exec_context) -> Any:
        """
        Execute data import.

        Args:
            node: DataNode with import configuration
            exec_context: Execution context

        Returns:
            None (stores result in context)
        """
        try:
            context = exec_context.get_all_variables()

            # Resolve source
            source = self.apply_databinding(node.source, context)

            # Build parameters
            params = self._build_params(node, context)

            # Execute data import
            result = self.services.data_import.import_data(
                node.data_type,
                source,
                params,
                context=exec_context
            )

            # Store result
            self._store_result(node, result, exec_context)

        except Exception as e:
            raise ExecutorError(f"Data import error in '{node.name}': {e}")

    def _build_params(self, node: DataNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for data import"""
        params = {
            'cache': node.cache,
            'ttl': node.ttl,
            'delimiter': node.delimiter,
            'quote': node.quote,
            'header': node.header,
            'encoding': node.encoding,
            'skip_rows': node.skip_rows,
            'xpath': node.xpath,
            'namespace': node.namespace,
            'columns': [],
            'fields': [],
            'transforms': [],
            'headers': []
        }

        # Add column definitions (for CSV)
        for col in node.columns:
            params['columns'].append({
                'name': col.name,
                'type': col.col_type,
                'required': col.required,
                'default': col.default
            })

        # Add field definitions (for XML)
        for field in node.fields:
            params['fields'].append({
                'name': field.name,
                'xpath': field.xpath,
                'type': field.field_type
            })

        # Add HTTP headers
        for header in node.headers:
            resolved_value = self.apply_databinding(header.value, context)
            params['headers'].append({
                'name': header.name,
                'value': resolved_value
            })

        # Add transformations
        for transform in node.transforms:
            for operation in transform.operations:
                op_dict = {
                    'type': operation.__class__.__name__.replace('Node', '').lower()
                }

                if hasattr(operation, 'condition'):
                    op_dict['condition'] = operation.condition
                elif hasattr(operation, 'by'):
                    op_dict['by'] = operation.by
                    op_dict['order'] = operation.order
                elif hasattr(operation, 'value'):
                    op_dict['value'] = operation.value
                elif hasattr(operation, 'field'):
                    op_dict['field'] = operation.field
                    op_dict['expression'] = operation.expression
                    op_dict['type'] = operation.comp_type

                params['transforms'].append(op_dict)

        return params

    def _store_result(self, node: DataNode, result, exec_context):
        """Store data import result in context"""
        exec_context.set_variable(node.name, result.data, scope="component")

        result_dict = {
            'success': result.success,
            'data': result.data,
            'error': result.error,
            'recordCount': result.recordCount,
            'loadTime': result.loadTime,
            'cached': result.cached,
            'source': result.source
        }

        exec_context.set_variable(f"{node.name}_result", result_dict, scope="component")

        if node.result:
            exec_context.set_variable(node.result, result_dict, scope="component")
