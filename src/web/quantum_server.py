"""
Quantum Web Server - Serve .q components as web pages

Usage:
    from web.quantum_server import QuantumServer

    server = QuantumServer()
    server.serve('components/', port=8000)
"""

from flask import Flask, request, send_from_directory, jsonify
from pathlib import Path
import sys
from typing import Dict, Any, Optional
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.simple_renderer import SimpleRenderer


class QuantumServer:
    """Web server for Quantum components"""

    def __init__(self, components_dir: str = "components", enable_hot_reload: bool = True):
        self.app = Flask(__name__)
        self.app.secret_key = 'quantum_dev_key_change_in_production'
        self.components_dir = Path(components_dir)
        self.renderer = SimpleRenderer()
        self.enable_hot_reload = enable_hot_reload
        self.hot_reload_watcher = None

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def index():
            """Serve index.q or list components"""
            index_file = self.components_dir / 'index.q'

            if index_file.exists():
                return self._render_component('index.q')
            else:
                return self._list_components()

        @self.app.route('/<path:component_path>')
        def serve_component(component_path):
            """Serve any .q component"""
            # Add .q extension if not present
            if not component_path.endswith('.q'):
                component_path = f"{component_path}.q"

            return self._render_component(component_path)

        @self.app.route('/api/<path:endpoint>', methods=['GET', 'POST', 'PUT', 'DELETE'])
        def api_endpoint(endpoint):
            """Handle API endpoints (from functions with rest config)"""
            # TODO: Integrate with REST API generator
            return jsonify({"error": "API not implemented yet"}), 501

        @self.app.errorhandler(404)
        def not_found(e):
            return self._render_error(404, "Component not found"), 404

        @self.app.errorhandler(500)
        def server_error(e):
            return self._render_error(500, f"Server error: {str(e)}"), 500

        @self.app.route('/__hot_reload__')
        def hot_reload_stream():
            """Server-Sent Events endpoint for hot reload"""
            if not self.enable_hot_reload:
                return "Hot reload disabled", 404

            from flask import stream_with_context, Response
            import time

            def event_stream():
                """Generator for SSE events"""
                try:
                    from runtime.hot_reload import get_sse_manager

                    messages = []

                    def listener(message):
                        messages.append(message)

                    sse_manager = get_sse_manager()
                    sse_manager.add_listener(listener)

                    # Send initial connection
                    yield f"data: {{'type': 'connected'}}\n\n"

                    while True:
                        if messages:
                            yield messages.pop(0)
                        else:
                            yield f": keepalive\n\n"
                            time.sleep(30)
                except GeneratorExit:
                    if 'sse_manager' in locals() and 'listener' in locals():
                        sse_manager.remove_listener(listener)

            return Response(
                stream_with_context(event_stream()),
                mimetype='text/event-stream',
                headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
            )

    def _render_component(self, component_path: str) -> str:
        """Render a .q component to HTML"""
        file_path = self.components_dir / component_path

        if not file_path.exists():
            return self._render_error(404, f"Component not found: {component_path}"), 404

        try:
            # Get query parameters as context
            context = dict(request.args)

            # Also include form data for POST requests
            if request.method == 'POST':
                context.update(request.form.to_dict())

            # Add request info to context
            context['query'] = dict(request.args)
            context['form'] = dict(request.form) if request.method == 'POST' else {}
            context['method'] = request.method
            context['path'] = request.path

            # Render component
            html = self.renderer.render_file(str(file_path), context)

            # Wrap in basic HTML structure
            full_html = self._wrap_html(html, component_path)

            return full_html

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return self._render_error(500, f"Error rendering component: {str(e)}", error_details), 500

    def _wrap_html(self, body: str, title: str = "Quantum App") -> str:
        """Wrap rendered HTML in basic HTML structure"""
        hot_reload_script = ""
        if self.enable_hot_reload:
            hot_reload_script = """
    <script>
    // Hot Reload Client
    (function() {
        const eventSource = new EventSource('/__hot_reload__');
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.type === 'reload') {
                console.log('🔄 Hot reload: ' + data.file);
                setTimeout(() => window.location.reload(), 300);
            }
        };
        eventSource.onerror = function() {
            console.log('❌ Hot reload connection lost');
        };
        console.log('🔥 Hot reload connected');
    })();
    </script>
"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }}
    </style>
</head>
<body>
    {body}
    {hot_reload_script}
</body>
</html>"""

    def _list_components(self) -> str:
        """List all available components"""
        components = []

        for file_path in self.components_dir.glob('**/*.q'):
            rel_path = file_path.relative_to(self.components_dir)
            components.append(str(rel_path))

        components.sort()

        html = "<h1>Available Components</h1><ul>"
        for comp in components:
            link = f"/{comp}"
            html += f'<li><a href="{link}">{comp}</a></li>'
        html += "</ul>"

        return self._wrap_html(html, "Component List")

    def _render_error(self, code: int, message: str, details: str = "") -> str:
        """Render error page"""
        html = f"""
        <div style="max-width: 800px; margin: 100px auto; padding: 40px; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <h1 style="color: #e74c3c;">Error {code}</h1>
            <p style="font-size: 1.2em; margin: 20px 0;">{message}</p>
            {f'<pre style="background: #f8f9fa; padding: 20px; border-radius: 4px; overflow-x: auto;"><code>{details}</code></pre>' if details else ''}
            <p style="margin-top: 20px;"><a href="/" style="color: #3498db;">← Back to home</a></p>
        </div>
        """
        return self._wrap_html(html, f"Error {code}")

    def serve(self, host: str = '0.0.0.0', port: int = 8000, debug: bool = True):
        """Start the web server"""
        print(f"""
╔══════════════════════════════════════════════════════════╗
║                 🚀 Quantum Server                        ║
╠══════════════════════════════════════════════════════════╣
║  Server running at: http://localhost:{port}              ║
║  Components dir: {self.components_dir}                   ║
║  Debug mode: {'ON' if debug else 'OFF'}                  ║
║  Hot reload: {'ON' if self.enable_hot_reload else 'OFF'} ║
╚══════════════════════════════════════════════════════════╝

Press Ctrl+C to stop
        """)

        # Start hot reload watcher if enabled
        if self.enable_hot_reload:
            try:
                from runtime.hot_reload import create_hot_reload_watcher

                self.hot_reload_watcher = create_hot_reload_watcher(
                    components_dir=str(self.components_dir),
                    examples_dir="examples" if Path("examples").exists() else None
                )
                self.hot_reload_watcher.start()
            except ImportError as e:
                print(f"⚠️  Hot reload unavailable: {e}")
                print("    Install watchdog: pip install watchdog")

        try:
            self.app.run(host=host, port=port, debug=debug, use_reloader=False)
        finally:
            if self.hot_reload_watcher:
                self.hot_reload_watcher.stop()


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Quantum Web Server')
    parser.add_argument('--dir', '-d', default='components', help='Components directory')
    parser.add_argument('--port', '-p', type=int, default=8000, help='Port number')
    parser.add_argument('--host', default='0.0.0.0', help='Host address')
    parser.add_argument('--no-debug', action='store_true', help='Disable debug mode')

    args = parser.parse_args()

    server = QuantumServer(components_dir=args.dir)
    server.serve(host=args.host, port=args.port, debug=not args.no_debug)


if __name__ == '__main__':
    main()
