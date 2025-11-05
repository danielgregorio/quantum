"""
Quantum Web Server - Serves .q components as HTML pages

ColdFusion-style simplicity: Just run `quantum start` and it works! 🪄
"""

import sys
import os
import yaml
from pathlib import Path
from flask import Flask, Response, request, send_from_directory, render_template_string
from typing import Dict, Any, Optional

# Fix imports
sys.path.append(str(Path(__file__).parent.parent))

from core.parser import QuantumParser, QuantumParseError
from runtime.component import ComponentRuntime
from runtime.renderer import HTMLRenderer
from runtime.execution_context import ExecutionContext


class QuantumWebServer:
    """
    Quantum Web Server - Magic happens here! ✨

    Automatically serves .q files as HTML pages.
    No configuration needed (but you can customize via quantum.config.yaml)
    """

    def __init__(self, config_path: str = 'quantum.config.yaml'):
        """
        Initialize Quantum Web Server.

        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.app = Flask(__name__)
        self.parser = QuantumParser()
        self.template_cache: Dict[str, Any] = {}  # AST cache

        # Setup routes
        self._setup_routes()

        # Print startup banner
        self._print_banner()


    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from YAML file with sensible defaults.

        Args:
            config_path: Path to config file

        Returns:
            Configuration dictionary
        """
        default_config = {
            'server': {
                'port': 8080,
                'host': '0.0.0.0',
                'reload': True,
                'debug': True
            },
            'paths': {
                'components': './components',
                'static': './static',
                'logs': './logs'
            },
            'defaults': {
                'component_type': 'pure',
                'interactive': False,
                'charset': 'utf-8',
                'timeout': 30
            },
            'performance': {
                'cache_templates': True,
                'cache_ttl': 300,
                'cache_max_size': 100
            },
            'security': {
                'xss_protection': True,
                'max_content_length': 16 * 1024 * 1024  # 16 MB
            },
            'logging': {
                'level': 'INFO',
                'console': True,
                'file': True,
                'filename': 'quantum.log'
            }
        }

        # Try to load config file
        config_file = Path(config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    user_config = yaml.safe_load(f) or {}
                    # Merge user config with defaults
                    default_config.update(user_config)
            except Exception as e:
                print(f"⚠️  Warning: Could not load config file: {e}")
                print(f"📝 Using default configuration")

        return default_config


    def _setup_routes(self):
        """Setup Flask routes for serving .q components"""

        @self.app.route('/')
        def index():
            """Serve index.q or show welcome page"""
            return self._serve_component('index')

        @self.app.route('/<path:component_path>')
        def dynamic_route(component_path):
            """Dynamically serve any .q component"""
            # Remove .q extension if provided
            if component_path.endswith('.q'):
                component_path = component_path[:-2]

            return self._serve_component(component_path)

        @self.app.route('/static/<path:filepath>')
        def serve_static(filepath):
            """Serve static files (CSS, JS, images)"""
            static_dir = self.config['paths']['static']
            return send_from_directory(static_dir, filepath)

        @self.app.errorhandler(404)
        def not_found(error):
            """404 handler with helpful message"""
            return self._render_error_page(
                title="404 - Component Not Found",
                message=f"The component you're looking for doesn't exist.",
                details=f"Requested path: {request.path}",
                suggestion="Check your components directory and try again."
            ), 404

        @self.app.errorhandler(500)
        def server_error(error):
            """500 handler with error details"""
            return self._render_error_page(
                title="500 - Server Error",
                message="An error occurred while processing your component.",
                details=str(error),
                suggestion="Check the component syntax and server logs."
            ), 500


    def _serve_component(self, component_path: str) -> Response:
        """
        Load, parse, execute, and render a .q component.

        Args:
            component_path: Path to component (without .q extension)

        Returns:
            Flask Response with rendered HTML
        """

        try:
            # Build full file path
            components_dir = self.config['paths']['components']
            file_path = Path(components_dir) / f'{component_path}.q'

            # Check if file exists
            if not file_path.exists():
                # Try index.q in subdirectory
                index_path = Path(components_dir) / component_path / 'index.q'
                if index_path.exists():
                    file_path = index_path
                else:
                    return self._render_welcome_page()

            # Check cache
            cache_enabled = self.config['performance']['cache_templates']
            cache_key = str(file_path)

            if cache_enabled and cache_key in self.template_cache:
                ast = self.template_cache[cache_key]
            else:
                # Parse component
                ast = self.parser.parse_file(str(file_path))

                # Cache if enabled
                if cache_enabled:
                    self.template_cache[cache_key] = ast

            # Prepare request parameters for component execution
            params = {}

            # Add query parameters
            query_params = dict(request.args)
            if query_params:
                params['query'] = query_params

            # Add form data if POST request
            if request.method == 'POST':
                form_data = dict(request.form)
                params['form'] = form_data

            # Execute component (runs queries, loops, functions, etc.)
            runtime = ComponentRuntime()
            runtime.execute_component(ast, params)

            # Render to HTML using runtime's execution context
            renderer = HTMLRenderer(runtime.execution_context)
            html = renderer.render(ast)

            return Response(html, mimetype='text/html')

        except QuantumParseError as e:
            return self._render_error_page(
                title="Parse Error",
                message="Could not parse component",
                details=str(e),
                suggestion="Check XML syntax and Quantum tag usage."
            ), 400

        except Exception as e:
            if self.config['server']['debug']:
                # Show detailed error in debug mode
                import traceback
                return self._render_error_page(
                    title="Runtime Error",
                    message="An error occurred during component execution",
                    details=traceback.format_exc(),
                    suggestion="Check component logic and data sources."
                ), 500
            else:
                # Generic error in production
                return self._render_error_page(
                    title="Error",
                    message="An error occurred",
                    details="Enable debug mode for more details.",
                    suggestion=""
                ), 500


    def _render_welcome_page(self) -> Response:
        """
        Render welcome page when index.q doesn't exist.

        Returns:
            Flask Response with welcome HTML
        """
        components_dir = self.config['paths']['components']

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to Quantum</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }}
                .container {{
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 15px;
                    padding: 40px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                }}
                h1 {{ margin-top: 0; font-size: 3em; }}
                code {{
                    background: rgba(0, 0, 0, 0.3);
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                }}
                .box {{
                    background: rgba(255, 255, 255, 0.1);
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                }}
                a {{
                    color: #fff;
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 Quantum is Running!</h1>
                <p>Your Quantum server is successfully running and ready to serve components.</p>

                <div class="box">
                    <h2>🎯 Quick Start</h2>
                    <p>Create your first component:</p>
                    <p><code>mkdir -p {components_dir}</code></p>
                    <p><code>nano {components_dir}/index.q</code></p>
                    <pre style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px;">
&lt;q:component name="HomePage"&gt;
  &lt;html&gt;
    &lt;body&gt;
      &lt;h1&gt;Hello from Quantum!&lt;/h1&gt;
      &lt;p&gt;This is my first component.&lt;/p&gt;
    &lt;/body&gt;
  &lt;/html&gt;
&lt;/q:component&gt;</pre>
                    <p>Then refresh this page!</p>
                </div>

                <div class="box">
                    <h2>📚 Learn More</h2>
                    <ul>
                        <li><a href="https://github.com/danielgregorio/quantum">Documentation</a></li>
                        <li><a href="/examples">Example Components</a></li>
                        <li><a href="/static">Static Files</a></li>
                    </ul>
                </div>

                <div class="box">
                    <h2>⚙️ Configuration</h2>
                    <p>Server is running with:</p>
                    <ul>
                        <li>Port: <code>{self.config['server']['port']}</code></li>
                        <li>Components directory: <code>{components_dir}</code></li>
                        <li>Debug mode: <code>{self.config['server']['debug']}</code></li>
                        <li>Auto-reload: <code>{self.config['server']['reload']}</code></li>
                    </ul>
                    <p>Edit <code>quantum.config.yaml</code> to customize.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return Response(html, mimetype='text/html')


    def _render_error_page(self, title: str, message: str, details: str, suggestion: str) -> str:
        """
        Render error page with helpful information.

        Args:
            title: Error title
            message: Error message
            details: Detailed error information
            suggestion: Suggestion for fixing the error

        Returns:
            HTML string
        """
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    max-width: 900px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .error-container {{
                    background: white;
                    border-radius: 10px;
                    padding: 40px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    border-left: 5px solid #e74c3c;
                }}
                h1 {{
                    color: #e74c3c;
                    margin-top: 0;
                }}
                .details {{
                    background: #f9f9f9;
                    border: 1px solid #ddd;
                    padding: 15px;
                    border-radius: 5px;
                    font-family: 'Courier New', monospace;
                    white-space: pre-wrap;
                    overflow-x: auto;
                }}
                .suggestion {{
                    background: #e8f5e9;
                    border-left: 4px solid #4caf50;
                    padding: 15px;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <h1>⚠️ {title}</h1>
                <p><strong>{message}</strong></p>

                {f'<div class="details">{details}</div>' if details else ''}

                {f'<div class="suggestion"><strong>💡 Suggestion:</strong> {suggestion}</div>' if suggestion else ''}

                <p style="margin-top: 30px;">
                    <a href="/">← Go back to home</a>
                </p>
            </div>
        </body>
        </html>
        """

        return html


    def _print_banner(self):
        """Print startup banner with server information"""
        port = self.config['server']['port']
        host = self.config['server']['host']
        components_dir = self.config['paths']['components']

        print("\n" + "="*60)
        print("🚀 QUANTUM WEB SERVER")
        print("="*60)
        print(f"📡 Server URL:      http://localhost:{port}")
        print(f"📂 Components:      {components_dir}")
        print(f"🔄 Auto-reload:     {self.config['server']['reload']}")
        print(f"🐛 Debug mode:      {self.config['server']['debug']}")
        print("="*60)
        print("✨ Magic is happening... Press Ctrl+C to stop")
        print("="*60 + "\n")


    def start(self):
        """Start the Quantum web server"""
        host = self.config['server']['host']
        port = self.config['server']['port']
        debug = self.config['server']['debug']
        reload = self.config['server']['reload']

        try:
            self.app.run(
                host=host,
                port=port,
                debug=debug,
                use_reloader=reload
            )
        except KeyboardInterrupt:
            print("\n👋 Quantum server stopped gracefully")
        except Exception as e:
            print(f"\n❌ Server error: {e}")


# Convenience function for CLI
def start_server(config_path: str = 'quantum.config.yaml'):
    """
    Start Quantum web server.

    Args:
        config_path: Path to configuration file
    """
    server = QuantumWebServer(config_path)
    server.start()


if __name__ == '__main__':
    start_server()
