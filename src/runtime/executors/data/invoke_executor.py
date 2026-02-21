"""
Invoke Executor - Execute q:invoke statements

Handles function, component, and HTTP invocations with caching.
"""

from typing import Any, List, Dict, Type
import json
from runtime.executors.base import BaseExecutor, ExecutorError
from core.features.invocation.src.ast_node import InvokeNode


class InvokeExecutor(BaseExecutor):
    """
    Executor for q:invoke statements.

    Supports:
    - Function invocation (local functions)
    - Component invocation (other .q components)
    - HTTP invocation (REST APIs)
    - Response caching with TTL
    """

    @property
    def handles(self) -> List[Type]:
        return [InvokeNode]

    def execute(self, node: InvokeNode, exec_context) -> Any:
        """
        Execute invocation.

        Args:
            node: InvokeNode with invocation configuration
            exec_context: Execution context

        Returns:
            None (stores result in context)
        """
        try:
            context = exec_context.get_all_variables()

            invocation_type = node.get_invocation_type()

            if invocation_type == "unknown":
                raise ExecutorError(
                    f"Invoke '{node.name}' requires one of: function, component, url, endpoint, or service"
                )

            # Build parameters based on type
            if invocation_type == "function":
                params = self._build_function_params(node, context)
            elif invocation_type == "component":
                params = self._build_component_params(node, context)
            elif invocation_type == "http":
                params = self._build_http_params(node, context)
            else:
                raise ExecutorError(f"Unsupported invocation type: {invocation_type}")

            # Check cache
            if node.cache:
                cache_key = f"invoke_{node.name}_{hash(str(params))}"
                cached = self.services.invocation.get_from_cache(cache_key)
                if cached is not None:
                    self._store_result(node, cached, exec_context)
                    return

            # Execute invocation
            result = self.services.invocation.invoke(
                invocation_type,
                params,
                context=self.runtime
            )

            # Cache result
            if node.cache and result.success:
                cache_key = f"invoke_{node.name}_{hash(str(params))}"
                self.services.invocation.put_in_cache(cache_key, result, node.ttl)

            # Store result
            self._store_result(node, result, exec_context)

        except Exception as e:
            raise ExecutorError(f"Invoke execution error in '{node.name}': {e}")

    def _build_function_params(self, node: InvokeNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for function invocation"""
        args = {}
        for param in node.params:
            param_value = self.apply_databinding(param.default if param.default else "", context)
            args[param.name] = param_value

        return {
            'function': node.function,
            'args': args
        }

    def _build_component_params(self, node: InvokeNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for component invocation"""
        args = {}
        for param in node.params:
            param_value = self.apply_databinding(param.default if param.default else "", context)
            args[param.name] = param_value

        return {
            'component': node.component,
            'args': args
        }

    def _build_http_params(self, node: InvokeNode, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for HTTP invocation"""
        url = self.apply_databinding(node.url, context)

        headers = {}
        for header_node in node.headers:
            header_value = self.apply_databinding(header_node.value, context)
            headers[header_node.name] = header_value

        if 'Content-Type' not in headers and 'content-type' not in headers:
            headers['Content-Type'] = node.content_type

        query_params = {}
        for param in node.params:
            param_value = self.apply_databinding(param.default if param.default else "", context)
            query_params[param.name] = param_value

        body = None
        if node.body:
            body = self.apply_databinding(node.body, context)
            if isinstance(body, str) and 'json' in node.content_type.lower():
                try:
                    body = json.loads(body)
                except:
                    pass

        return {
            'url': url,
            'method': node.method,
            'headers': headers,
            'params': query_params,
            'body': body,
            'auth_type': node.auth_type,
            'auth_token': self.apply_databinding(node.auth_token, context) if node.auth_token else None,
            'auth_header': node.auth_header,
            'auth_username': self.apply_databinding(node.auth_username, context) if node.auth_username else None,
            'auth_password': self.apply_databinding(node.auth_password, context) if node.auth_password else None,
            'timeout': node.timeout,
            'retry': node.retry,
            'retry_delay': node.retry_delay,
            'response_format': node.response_format
        }

    def _store_result(self, node: InvokeNode, result, exec_context):
        """Store invocation result in context"""
        exec_context.set_variable(node.name, result.data, scope="component")

        result_dict = {
            'success': result.success,
            'data': result.data,
            'error': result.error,
            'executionTime': result.execution_time,
            'invocationType': result.invocation_type,
            'metadata': result.metadata
        }

        exec_context.set_variable(f"{node.name}_result", result_dict, scope="component")

        if node.result:
            exec_context.set_variable(node.result, result_dict, scope="component")
