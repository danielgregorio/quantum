"""
Invocation Feature - Runtime
Handles execution of all invocation types (functions, components, HTTP, etc.)
"""

import time
import json
import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import base64


@dataclass
class InvocationResult:
    """Result object for all invocations"""
    success: bool
    data: Any = None
    error: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0
    invocation_type: str = ""
    metadata: Optional[Dict[str, Any]] = None


class InvocationService:
    """Service to handle all types of invocations"""

    def __init__(self):
        self.cache: Dict[str, Any] = {}  # Simple in-memory cache

    def invoke(
        self,
        invocation_type: str,
        params: Dict[str, Any],
        context: Any = None
    ) -> InvocationResult:
        """Main invocation dispatcher"""
        start_time = time.time()

        try:
            if invocation_type == "function":
                result = self._invoke_function(params, context)
            elif invocation_type == "component":
                result = self._invoke_component(params, context)
            elif invocation_type == "http":
                result = self._invoke_http(params)
            else:
                return InvocationResult(
                    success=False,
                    error={"message": f"Unknown invocation type: {invocation_type}"},
                    invocation_type=invocation_type
                )

            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            result.execution_time = execution_time
            result.invocation_type = invocation_type
            return result

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return InvocationResult(
                success=False,
                error={
                    "message": str(e),
                    "type": type(e).__name__
                },
                execution_time=execution_time,
                invocation_type=invocation_type
            )

    def _invoke_function(self, params: Dict[str, Any], context: Any) -> InvocationResult:
        """Invoke local function"""
        function_name = params.get('function')
        function_args = params.get('args', {})

        if not context:
            return InvocationResult(
                success=False,
                error={"message": "Context required for function invocation"}
            )

        # Get function from context (ComponentRuntime will handle this)
        if not hasattr(context, 'get_function'):
            return InvocationResult(
                success=False,
                error={"message": "Context does not support function invocation"}
            )

        func = context.get_function(function_name)
        if not func:
            return InvocationResult(
                success=False,
                error={"message": f"Function '{function_name}' not found"}
            )

        # Execute function
        result = context.execute_function(function_name, function_args)

        return InvocationResult(
            success=result.get('success', False),
            data=result.get('data'),
            error=result.get('error'),
            metadata=result
        )

    def _invoke_component(self, params: Dict[str, Any], context: Any) -> InvocationResult:
        """Invoke local component"""
        component_name = params.get('component')
        component_args = params.get('args', {})

        if not context:
            return InvocationResult(
                success=False,
                error={"message": "Context required for component invocation"}
            )

        # Get component from context (ComponentRuntime will handle this)
        if not hasattr(context, 'execute_component'):
            return InvocationResult(
                success=False,
                error={"message": "Context does not support component invocation"}
            )

        result = context.execute_component(component_name, component_args)

        return InvocationResult(
            success=result.get('success', False),
            data=result.get('data'),
            error=result.get('error'),
            metadata=result
        )

    def _invoke_http(self, params: Dict[str, Any]) -> InvocationResult:
        """Invoke HTTP/REST endpoint"""
        url = params.get('url')
        method = params.get('method', 'GET').upper()
        headers = params.get('headers', {})
        query_params = params.get('params', {})
        body = params.get('body')
        auth_type = params.get('auth_type')
        timeout_ms = params.get('timeout', 30000)
        retry = params.get('retry', 0)
        retry_delay = params.get('retry_delay', 1000)
        response_format = params.get('response_format', 'auto')

        if not url:
            return InvocationResult(
                success=False,
                error={"message": "URL required for HTTP invocation"}
            )

        # Build authentication
        headers = self._build_auth_headers(params, headers)

        # Convert timeout to seconds for requests library
        timeout_sec = timeout_ms / 1000

        # Retry logic
        last_error = None
        for attempt in range(retry + 1):
            try:
                # Make HTTP request
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=query_params,
                    json=body if method in ['POST', 'PUT', 'PATCH'] and isinstance(body, dict) else None,
                    data=body if method in ['POST', 'PUT', 'PATCH'] and isinstance(body, str) else None,
                    timeout=timeout_sec
                )

                # Parse response based on format
                data = self._parse_http_response(response, response_format)

                # Build metadata
                metadata = {
                    "status_code": response.status_code,
                    "status_text": response.reason,
                    "headers": dict(response.headers),
                    "url": response.url,
                    "attempts": attempt + 1
                }

                # Check if response is successful
                success = 200 <= response.status_code < 300

                if not success:
                    return InvocationResult(
                        success=False,
                        data=data,
                        error={
                            "message": f"HTTP {response.status_code}: {response.reason}",
                            "status_code": response.status_code
                        },
                        metadata=metadata
                    )

                return InvocationResult(
                    success=True,
                    data=data,
                    metadata=metadata
                )

            except requests.exceptions.Timeout as e:
                last_error = InvocationResult(
                    success=False,
                    error={
                        "message": f"Request timeout after {timeout_ms}ms",
                        "type": "TimeoutError"
                    },
                    metadata={"attempts": attempt + 1}
                )

            except requests.exceptions.ConnectionError as e:
                last_error = InvocationResult(
                    success=False,
                    error={
                        "message": f"Connection error: {str(e)}",
                        "type": "ConnectionError"
                    },
                    metadata={"attempts": attempt + 1}
                )

            except Exception as e:
                last_error = InvocationResult(
                    success=False,
                    error={
                        "message": str(e),
                        "type": type(e).__name__
                    },
                    metadata={"attempts": attempt + 1}
                )

            # If we have more retries, wait before retrying
            if attempt < retry:
                time.sleep(retry_delay / 1000)  # Convert ms to seconds

        # All retries exhausted, return last error
        return last_error

    def _build_auth_headers(self, params: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, str]:
        """Build authentication headers"""
        auth_type = params.get('auth_type')
        headers = headers.copy()  # Don't mutate original

        if auth_type == 'bearer':
            token = params.get('auth_token')
            if token:
                headers['Authorization'] = f'Bearer {token}'

        elif auth_type == 'apikey':
            token = params.get('auth_token')
            header_name = params.get('auth_header', 'Authorization')
            if token:
                headers[header_name] = token

        elif auth_type == 'basic':
            username = params.get('auth_username')
            password = params.get('auth_password')
            if username and password:
                credentials = f"{username}:{password}".encode('utf-8')
                encoded = base64.b64encode(credentials).decode('utf-8')
                headers['Authorization'] = f'Basic {encoded}'

        return headers

    def _parse_http_response(self, response: requests.Response, response_format: str) -> Any:
        """Parse HTTP response based on format"""
        if response_format == 'auto':
            # Try to detect format from Content-Type header
            content_type = response.headers.get('Content-Type', '').lower()

            if 'application/json' in content_type:
                try:
                    return response.json()
                except:
                    return response.text

            elif 'text/' in content_type or 'application/xml' in content_type:
                return response.text

            elif 'application/octet-stream' in content_type or 'image/' in content_type:
                return {
                    "binary": True,
                    "content_type": content_type,
                    "size": len(response.content)
                }

            else:
                # Default to text
                return response.text

        elif response_format == 'json':
            try:
                return response.json()
            except:
                return {"error": "Failed to parse JSON response", "text": response.text}

        elif response_format == 'text':
            return response.text

        elif response_format == 'xml':
            return response.text

        elif response_format == 'binary':
            return {
                "binary": True,
                "content_type": response.headers.get('Content-Type'),
                "size": len(response.content)
            }

        else:
            return response.text

    def get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get value from cache"""
        return self.cache.get(cache_key)

    def put_in_cache(self, cache_key: str, value: Any, ttl: Optional[int] = None):
        """Put value in cache"""
        # Simple implementation - in production you'd use TTL properly
        self.cache[cache_key] = value

    def clear_cache(self):
        """Clear all cache"""
        self.cache.clear()
