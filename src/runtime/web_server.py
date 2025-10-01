"""
Quantum Web Server - Web server for Quantum HTML applications
"""

import sys
from pathlib import Path
from flask import Flask, jsonify, request
from typing import Dict, Any

# Fix imports
sys.path.append(str(Path(__file__).parent.parent))

from core.ast_nodes import ApplicationNode, QuantumRoute

class QuantumWebServer:
    """Web server for Quantum HTML applications"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.app = Flask(__name__)
        self.routes: Dict[str, Dict[str, Any]] = {}
        self._setup_default_routes()
    
    def _setup_default_routes(self):
        """Configure default routes"""
        @self.app.route('/', methods=['GET'])
        def index():
            return self._generate_index_page()
    
    def _generate_index_page(self) -> str:
        """Generate index page with routes list"""
        routes_list = "\n".join([
            f"<li><a href='{route}'>{route}</a> ({info['method']})</li>" 
            for route, info in self.routes.items()
        ])
        
        return f"""
        <html>
        <head><title>Quantum Web Server</title></head>
        <body>
            <h1>🚀 Quantum Web Server</h1>
            <p>Server running successfully!</p>
            <hr>
            <h3>Available routes:</h3>
            <ul>{routes_list}</ul>
        </body>
        </html>
        """
    
    def configure_from_ast(self, app_node: ApplicationNode):
        """Configure server based on application AST"""
        for route in app_node.routes:
            self._add_route_from_ast(route)
    
    def _add_route_from_ast(self, route: QuantumRoute):
        """Add route based on AST"""
        path = route.path
        method = route.method
        
        # Get first q:return from route
        content = ""
        if route.returns:
            content = route.returns[0].value or "No content"
        
        self._add_route(path, method, content)
    
    def _add_route(self, path: str, method: str, content: str):
        """Add route to Flask"""
        self.routes[path] = {'method': method, 'content': content}
        
        def route_handler():
            return self._process_content(content)
        
        # Unique name for function
        route_handler.__name__ = f"route_{path.replace('/', '_').replace('-', '_')}"
        
        # Add to Flask
        self.app.add_url_rule(path, route_handler.__name__, route_handler, methods=[method])
    
    def _process_content(self, content: str) -> str:
        """Process route content"""
        # If it looks like HTML, return directly
        if '<' in content and '>' in content:
            return content
        
        # Otherwise, wrap in basic HTML
        return f"""
        <html>
        <body>
            <h1>Quantum Response</h1>
            <p>{content}</p>
        </body>
        </html>
        """
    
    def start(self):
        """Start web server"""
        print(f"🌐 Quantum Web Server starting on port {self.port}")
        print(f"🔗 Access: http://localhost:{self.port}")
        print("🛑 To stop: Ctrl+C")
        
        try:
            self.app.run(host='0.0.0.0', port=self.port, debug=False)
        except KeyboardInterrupt:
            print("\n👋 Server stopped by user")
        except Exception as e:
            print(f"❌ Server error: {e}")
