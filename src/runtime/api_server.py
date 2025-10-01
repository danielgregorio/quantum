"""
Quantum API Server - API server for Quantum microservices
"""

import sys
from pathlib import Path
from flask import Flask, jsonify, request
import json
from typing import Dict, Any

# Fix imports
sys.path.append(str(Path(__file__).parent.parent))

from core.ast_nodes import ApplicationNode, QuantumRoute

class QuantumAPIServer:
    """API server for Quantum microservices"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.app = Flask(__name__)
        self.routes: Dict[str, Dict[str, Any]] = {}
        self._setup_default_routes()
    
    def _setup_default_routes(self):
        """Configure default API routes"""
        @self.app.route('/health', methods=['GET'])
        def health_check():
            return jsonify({
                "status": "healthy",
                "server": "Quantum API",
                "routes": list(self.routes.keys())
            })
    
    def configure_from_ast(self, app_node: ApplicationNode):
        """Configure API based on application AST"""
        for route in app_node.routes:
            self._add_route_from_ast(route)
    
    def _add_route_from_ast(self, route: QuantumRoute):
        """Add API route based on AST"""
        path = route.path
        method = route.method
        
        # Get first q:return from route
        content = "{}"
        if route.returns:
            content = route.returns[0].value or "{}"
        
        self._add_api_route(path, method, content)
    
    def _add_api_route(self, path: str, method: str, content: str):
        """Add API route to Flask"""
        self.routes[path] = {'method': method, 'content': content}
        
        def api_handler():
            return self._process_json_content(content)
        
        # Unique name for function
        api_handler.__name__ = f"api_{path.replace('/', '_').replace('-', '_')}"
        
        # Add to Flask
        self.app.add_url_rule(path, api_handler.__name__, api_handler, methods=[method])
    
    def _process_json_content(self, content: str):
        """Process content as JSON"""
        try:
            # Try to parse JSON
            parsed = json.loads(content)
            return jsonify(parsed)
        except json.JSONDecodeError:
            # If not valid JSON, return as text
            return jsonify({"result": content, "type": "text"})
    
    def start(self):
        """Start API server"""
        print(f"🛠️  Quantum API Server starting on port {self.port}")
        print(f"🔗 API: http://localhost:{self.port}")
        print(f"🩺 Health: http://localhost:{self.port}/health")
        print("🛑 To stop: Ctrl+C")
        
        try:
            self.app.run(host='0.0.0.0', port=self.port, debug=False)
        except KeyboardInterrupt:
            print("\n👋 API server stopped by user")
        except Exception as e:
            print(f"❌ Server error: {e}")
