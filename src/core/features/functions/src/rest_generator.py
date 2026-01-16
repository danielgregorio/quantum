"""
REST API Auto-Generator from q:function

Automatically generates REST endpoints from functions with rest configuration.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
from pathlib import Path

# Import function nodes
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.features.functions.src import FunctionNode
from core.ast_nodes import ComponentNode, ApplicationNode


@dataclass
class RestEndpoint:
    """Represents a generated REST endpoint"""
    path: str
    method: str
    function_name: str
    function: FunctionNode
    auth_required: bool = False
    roles: List[str] = None
    rate_limit: Optional[str] = None
    produces: str = "application/json"
    consumes: str = "application/json"
    status_code: int = 200

    def __post_init__(self):
        if self.roles is None:
            self.roles = []


class RestAPIGenerator:
    """Generates REST API from functions"""

    def __init__(self):
        self.endpoints: List[RestEndpoint] = []

    def generate_from_component(self, component: ComponentNode) -> List[RestEndpoint]:
        """
        Extract all functions with REST configuration from component

        Returns list of REST endpoints
        """
        endpoints = []

        for statement in component.statements:
            if isinstance(statement, FunctionNode) and statement.is_rest_enabled():
                endpoint = self._create_endpoint(statement)
                endpoints.append(endpoint)

        self.endpoints.extend(endpoints)
        return endpoints

    def generate_from_application(self, application: ApplicationNode) -> List[RestEndpoint]:
        """
        Extract all REST-enabled functions from application and components

        Returns list of REST endpoints
        """
        endpoints = []

        # Scan all components in application
        for component in application.components:
            component_endpoints = self.generate_from_component(component)
            endpoints.extend(component_endpoints)

        return endpoints

    def _create_endpoint(self, function: FunctionNode) -> RestEndpoint:
        """Create REST endpoint from function"""
        config = function.rest_config

        return RestEndpoint(
            path=config.endpoint,
            method=config.method,
            function_name=function.name,
            function=function,
            auth_required=config.auth is not None,
            roles=config.roles or [],
            rate_limit=config.rate_limit,
            produces=config.produces,
            consumes=config.consumes,
            status_code=config.status
        )

    def generate_flask_routes(self) -> str:
        """
        Generate Flask route code from endpoints

        Returns Python code as string
        """
        lines = []
        lines.append("from flask import Flask, request, jsonify")
        lines.append("from functools import wraps")
        lines.append("")
        lines.append("app = Flask(__name__)")
        lines.append("")

        # Generate auth decorator if needed
        if any(e.auth_required for e in self.endpoints):
            lines.append("def require_auth(f):")
            lines.append("    @wraps(f)")
            lines.append("    def decorated(*args, **kwargs):")
            lines.append("        # TODO: Implement authentication")
            lines.append("        token = request.headers.get('Authorization')")
            lines.append("        if not token:")
            lines.append("            return jsonify({'error': 'Unauthorized'}), 401")
            lines.append("        return f(*args, **kwargs)")
            lines.append("    return decorated")
            lines.append("")

        # Generate each endpoint
        for endpoint in self.endpoints:
            lines.extend(self._generate_flask_route(endpoint))
            lines.append("")

        lines.append("if __name__ == '__main__':")
        lines.append("    app.run(debug=True)")

        return "\n".join(lines)

    def _generate_flask_route(self, endpoint: RestEndpoint) -> List[str]:
        """Generate Flask route for single endpoint"""
        lines = []

        # Route decorator
        lines.append(f"@app.route('{endpoint.path}', methods=['{endpoint.method}'])")

        # Auth decorator if needed
        if endpoint.auth_required:
            lines.append("@require_auth")

        # Function definition
        func_name = f"api_{endpoint.function_name}"
        lines.append(f"def {func_name}():")

        # Extract parameters
        lines.append("    # Extract parameters")
        if endpoint.method in ['POST', 'PUT', 'PATCH']:
            lines.append("    data = request.get_json()")
        else:
            lines.append("    data = request.args.to_dict()")

        # Call function runtime
        lines.append(f"    # Call Quantum function: {endpoint.function_name}")
        lines.append(f"    from core.features.functions.src import call_function")
        lines.append(f"    result = call_function('{endpoint.function_name}', data, {{}})")

        # Return response
        lines.append(f"    return jsonify(result), {endpoint.status_code}")

        return lines

    def generate_fastapi_routes(self) -> str:
        """
        Generate FastAPI route code from endpoints

        Returns Python code as string
        """
        lines = []
        lines.append("from fastapi import FastAPI, HTTPException, Depends, Header")
        lines.append("from pydantic import BaseModel")
        lines.append("from typing import Optional")
        lines.append("")
        lines.append("app = FastAPI()")
        lines.append("")

        # Generate models for each endpoint
        for endpoint in self.endpoints:
            if endpoint.function.params:
                lines.extend(self._generate_pydantic_model(endpoint))
                lines.append("")

        # Generate auth dependency if needed
        if any(e.auth_required for e in self.endpoints):
            lines.append("async def verify_token(authorization: Optional[str] = Header(None)):")
            lines.append("    if not authorization:")
            lines.append("        raise HTTPException(status_code=401, detail='Unauthorized')")
            lines.append("    # TODO: Implement token verification")
            lines.append("    return True")
            lines.append("")

        # Generate each endpoint
        for endpoint in self.endpoints:
            lines.extend(self._generate_fastapi_route(endpoint))
            lines.append("")

        return "\n".join(lines)

    def _generate_pydantic_model(self, endpoint: RestEndpoint) -> List[str]:
        """Generate Pydantic model for endpoint parameters"""
        lines = []
        model_name = f"{endpoint.function_name.capitalize()}Request"

        lines.append(f"class {model_name}(BaseModel):")

        for param in endpoint.function.params:
            # Map Quantum types to Python types
            type_map = {
                "string": "str",
                "number": "float",
                "boolean": "bool",
                "object": "dict",
                "array": "list",
                "any": "Any"
            }
            python_type = type_map.get(param.type, "str")

            if not param.required:
                python_type = f"Optional[{python_type}]"
                default = f" = {param.default}" if param.default else " = None"
            else:
                default = ""

            lines.append(f"    {param.name}: {python_type}{default}")

        return lines

    def _generate_fastapi_route(self, endpoint: RestEndpoint) -> List[str]:
        """Generate FastAPI route for single endpoint"""
        lines = []

        # Route decorator
        method_lower = endpoint.method.lower()
        auth_dependency = ", dependencies=[Depends(verify_token)]" if endpoint.auth_required else ""

        lines.append(f"@app.{method_lower}('{endpoint.path}'{auth_dependency})")

        # Function signature
        func_name = f"api_{endpoint.function_name}"

        if endpoint.function.params:
            model_name = f"{endpoint.function_name.capitalize()}Request"
            lines.append(f"async def {func_name}(request: {model_name}):")
            lines.append("    data = request.dict()")
        else:
            lines.append(f"async def {func_name}():")
            lines.append("    data = {}")

        # Call function runtime
        lines.append(f"    # Call Quantum function: {endpoint.function_name}")
        lines.append(f"    from core.features.functions.src import call_function")
        lines.append(f"    result = call_function('{endpoint.function_name}', data, {{}})")

        # Return response
        lines.append(f"    return result")

        return lines

    def generate_openapi_spec(self, title: str = "Quantum API", version: str = "1.0.0") -> Dict[str, Any]:
        """
        Generate OpenAPI 3.0 specification

        Returns OpenAPI spec as dict (can be serialized to JSON/YAML)
        """
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": title,
                "version": version,
                "description": "Auto-generated API from Quantum functions"
            },
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {}
            }
        }

        # Add security schemes if any endpoint requires auth
        if any(e.auth_required for e in self.endpoints):
            spec["components"]["securitySchemes"]["bearerAuth"] = {
                "type": "http",
                "scheme": "bearer"
            }

        # Generate paths
        for endpoint in self.endpoints:
            path_item = self._generate_openapi_path(endpoint)

            if endpoint.path not in spec["paths"]:
                spec["paths"][endpoint.path] = {}

            spec["paths"][endpoint.path][endpoint.method.lower()] = path_item

        return spec

    def _generate_openapi_path(self, endpoint: RestEndpoint) -> Dict[str, Any]:
        """Generate OpenAPI path item for endpoint"""
        path_item = {
            "summary": f"{endpoint.function_name}",
            "description": endpoint.function.description or f"Calls {endpoint.function_name} function",
            "operationId": endpoint.function_name,
            "responses": {
                str(endpoint.status_code): {
                    "description": "Successful response",
                    "content": {
                        endpoint.produces: {
                            "schema": {
                                "type": "object"
                            }
                        }
                    }
                }
            }
        }

        # Add parameters
        if endpoint.function.params:
            if endpoint.method in ['GET', 'DELETE']:
                # Query parameters
                path_item["parameters"] = []
                for param in endpoint.function.params:
                    path_item["parameters"].append({
                        "name": param.name,
                        "in": "query",
                        "required": param.required,
                        "schema": {
                            "type": self._openapi_type(param.type),
                            "default": param.default
                        },
                        "description": param.description
                    })
            else:
                # Request body
                properties = {}
                required = []

                for param in endpoint.function.params:
                    properties[param.name] = {
                        "type": self._openapi_type(param.type),
                        "description": param.description
                    }
                    if param.default:
                        properties[param.name]["default"] = param.default

                    if param.required:
                        required.append(param.name)

                path_item["requestBody"] = {
                    "required": len(required) > 0,
                    "content": {
                        endpoint.consumes: {
                            "schema": {
                                "type": "object",
                                "properties": properties,
                                "required": required
                            }
                        }
                    }
                }

        # Add security if auth required
        if endpoint.auth_required:
            path_item["security"] = [{"bearerAuth": []}]

        return path_item

    def _openapi_type(self, quantum_type: str) -> str:
        """Map Quantum type to OpenAPI type"""
        type_map = {
            "string": "string",
            "number": "number",
            "boolean": "boolean",
            "object": "object",
            "array": "array",
            "any": "string"
        }
        return type_map.get(quantum_type, "string")

    def save_openapi_spec(self, output_path: str, title: str = "Quantum API", version: str = "1.0.0"):
        """Save OpenAPI spec to JSON file"""
        spec = self.generate_openapi_spec(title, version)

        with open(output_path, 'w') as f:
            json.dump(spec, f, indent=2)

        print(f"✅ OpenAPI spec saved to {output_path}")
