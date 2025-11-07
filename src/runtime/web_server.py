"""
Quantum Web Server - Serves .q components as HTML pages

ColdFusion-style simplicity: Just run `quantum start` and it works! 🪄
"""

import sys
import os
import yaml
from pathlib import Path
from flask import Flask, Response, request, send_from_directory, render_template_string, session, redirect
from typing import Dict, Any, Optional
import secrets

# Fix imports
sys.path.append(str(Path(__file__).parent.parent))

from core.parser import QuantumParser, QuantumParseError
from core.ast_nodes import ActionNode
from runtime.component import ComponentRuntime
from runtime.renderer import HTMLRenderer
from runtime.execution_context import ExecutionContext
from runtime.action_handler import ActionHandler
from runtime.auth_service import AuthService, AuthorizationError
from runtime.error_handler import ErrorHandler, QuantumError


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

        # Setup secret key for sessions (flash messages)
        self.app.secret_key = secrets.token_hex(32)

        self.parser = QuantumParser()
        self.template_cache: Dict[str, Any] = {}  # AST cache
        self.action_handler = ActionHandler()

        # Phase F: Application scope (global state shared across all users)
        self.application_scope: Dict[str, Any] = {}

        # Statistics for success tracking
        self.stats = {
            'components_served': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }

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

        @self.app.route('/', methods=['GET', 'POST', 'PUT', 'DELETE'])
        def index():
            """Serve index.q or show welcome page"""
            return self._serve_component('index')

        @self.app.route('/<path:component_path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
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

        @self.app.route('/_health')
        @self.app.route('/_status')
        def health_check():
            """Health check endpoint - shows server status and statistics"""
            return self._render_health_page()

        @self.app.route('/_partial/<path:component_path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
        def serve_partial(component_path):
            """
            Serve partial component for HTMX requests (Phase B)

            Partials return only the component HTML without full page wrapper.
            Used for HTMX-style progressive enhancement.
            """
            # Remove .q extension if provided
            if component_path.endswith('.q'):
                component_path = component_path[:-2]

            return self._serve_component(component_path, partial=True)

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


    def _serve_component(self, component_path: str, partial: bool = False) -> Response:
        """
        Load, parse, execute, and render a .q component.

        Args:
            component_path: Path to component (without .q extension)
            partial: If True, return only component HTML for HTMX (Phase B)

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
                self.stats['cache_hits'] += 1
                if self.config['server']['debug']:
                    print(f"[DEBUG] ✅ Component loaded from cache: {component_path}")
            else:
                # Parse component
                ast = self.parser.parse_file(str(file_path))
                self.stats['cache_misses'] += 1
                print(f"[SUCCESS] ✅ Component parsed successfully: {component_path}")

                # Cache if enabled
                if cache_enabled:
                    self.template_cache[cache_key] = ast
                    if self.config['server']['debug']:
                        print(f"[DEBUG] Component cached: {component_path}")

            # Phase G: Authentication & Security - Check authorization
            if 'quantum_session' not in session:
                session['quantum_session'] = {}

            session_data = session['quantum_session']

            # Check if component requires authentication
            if ast.require_auth:
                if not AuthService.is_authenticated(session_data):
                    # Not authenticated - redirect to login
                    session['redirect_after_login'] = request.path
                    return redirect('/login')

                # Check session expiry
                if AuthService.is_session_expired(session_data):
                    # Session expired - logout and redirect to login
                    AuthService.logout(session_data)
                    session.modified = True
                    return redirect('/login?expired=true')

                # Check role requirement
                if ast.require_role:
                    if not AuthService.has_role(session_data, ast.require_role):
                        # Forbidden - user doesn't have required role
                        return Response(
                            f"<h1>403 Forbidden</h1><p>Required role: {ast.require_role}</p>",
                            status=403,
                            mimetype='text/html'
                        )

                # Check permission requirement
                if ast.require_permission:
                    if not AuthService.has_permission(session_data, ast.require_permission):
                        # Forbidden - user doesn't have required permission
                        return Response(
                            f"<h1>403 Forbidden</h1><p>Required permission: {ast.require_permission}</p>",
                            status=403,
                            mimetype='text/html'
                        )

            # Check if this is an action request (POST/PUT/DELETE)
            if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                # Look for q:action in component
                action_node = self._find_action_in_component(ast)

                if action_node:
                    # Handle action
                    redirect_url, status_code = self.action_handler.handle_action(action_node)

                    if redirect_url:
                        return redirect(redirect_url, code=status_code)
                    # If no redirect, fall through to render component

            # Prepare request parameters for component execution
            params = {}

            # Add query parameters
            query_params = dict(request.args)
            if query_params:
                params['query'] = query_params

            # Add form data if POST request (for non-action processing)
            if request.method == 'POST':
                form_data = dict(request.form)
                params['form'] = form_data

            # Get flash message if present
            flash_data = self.action_handler.get_flash_message()
            if flash_data:
                params['flash'] = flash_data['message']
                params['flashType'] = flash_data['type']

            # Phase F: Setup scopes for ExecutionContext
            # Session scope - user-specific, persistent (from Flask session)
            if 'quantum_session' not in session:
                session['quantum_session'] = {}
            params['_session_scope'] = session['quantum_session']

            # Application scope - global, shared across all users
            params['_application_scope'] = self.application_scope

            # Request scope - request-specific, cleared after response
            params['_request_scope'] = {
                'method': request.method,
                'path': request.path,
                'url': request.url
            }

            # Execute component (runs queries, loops, functions, etc.)
            runtime = ComponentRuntime()
            runtime.execute_component(ast, params)

            # Phase F: Sync session back to Flask session
            session['quantum_session'] = runtime.execution_context.session_vars
            session.modified = True

            # Render to HTML using runtime's execution context
            renderer = HTMLRenderer(runtime.execution_context)
            html = renderer.render(ast)

            # Track successful render
            self.stats['components_served'] += 1

            # Log success
            request_type = "partial" if partial else "full page"
            print(f"[SUCCESS] ✅ Component rendered successfully: {component_path} ({request_type}) [Total: {self.stats['components_served']}]")

            if self.config['server']['debug'] and self.stats['components_served'] % 10 == 0:
                print(f"[STATS] 📊 Cache hits: {self.stats['cache_hits']}, misses: {self.stats['cache_misses']}")

            # Phase B: For partial requests, return only component HTML
            if partial:
                return Response(html, mimetype='text/html')

            # For full page requests, wrap with HTMX support
            full_html = self._wrap_with_htmx(html, component_path)

            return Response(full_html, mimetype='text/html')

        except QuantumParseError as e:
            # Enhanced parse error with context
            enhanced_error = ErrorHandler.handle_parse_error(e, component_path)

            if self.config['server']['debug']:
                # Show enhanced error in debug mode
                return self._render_error_page(
                    title="Parse Error",
                    message=f"Could not parse component: {component_name}",
                    details=str(enhanced_error),
                    suggestion="Check XML syntax and Quantum tag usage. Use 'quantum inspect {component_name}' for details."
                ), 400
            else:
                return self._render_error_page(
                    title="Parse Error",
                    message="Could not parse component",
                    details="Enable debug mode for details",
                    suggestion=""
                ), 400

        except QuantumError as e:
            # Already enhanced error
            return self._render_error_page(
                title="Quantum Error",
                message=e.message,
                details=str(e),
                suggestion=e.suggestion or "Check the error details above"
            ), 500

        except Exception as e:
            if self.config['server']['debug']:
                # Enhanced runtime error
                enhanced_error = ErrorHandler.handle_runtime_error(e, component_name, component_path)

                import traceback
                return self._render_error_page(
                    title="Runtime Error",
                    message=f"Error in component: {component_name}",
                    details=str(enhanced_error) + "\n\n" + traceback.format_exc(),
                    suggestion="Use 'quantum inspect {component_name}' to debug. Check component logic and data sources."
                ), 500
            else:
                # Generic error in production
                return self._render_error_page(
                    title="Error",
                    message="An error occurred",
                    details="Enable debug mode for more details.",
                    suggestion=""
                ), 500

    def _wrap_with_htmx(self, html: str, component_name: str) -> str:
        """
        Wrap component HTML with HTMX library support (Phase B).

        Adds:
        - HTMX library from CDN
        - Minimal CSS reset
        - HTMX configuration

        Args:
            html: Rendered component HTML
            component_name: Component name for title

        Returns:
            Full HTML page with HTMX support
        """
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{component_name} - Quantum</title>

    <!-- Phase B: HTMX for Progressive Enhancement -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>

    <style>
        /* Minimal CSS reset */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
        }}

        /* HTMX Loading indicators */
        .htmx-indicator {{
            display: none;
        }}

        .htmx-request .htmx-indicator {{
            display: inline;
        }}

        .htmx-request.htmx-indicator {{
            display: inline;
        }}

        /* Loading spinner */
        .htmx-indicator:after {{
            content: "⏳";
            margin-left: 8px;
        }}
    </style>
</head>
<body>
    {html}

    <!-- HTMX Configuration -->
    <script>
        // Configure HTMX
        htmx.config.defaultSwapStyle = "innerHTML";
        htmx.config.defaultSwapDelay = 0;
        htmx.config.historyCacheSize = 10;

        // Log HTMX events in debug mode
        if (window.location.hostname === 'localhost') {{
            htmx.logAll();
        }}
    </script>
</body>
</html>"""

    def _render_health_page(self) -> Response:
        """
        Render health check page showing server status and statistics.

        Returns:
            Flask Response with health check HTML
        """
        components_dir = Path(self.config['paths']['components'])

        # Scan for available components
        available_components = []
        if components_dir.exists():
            available_components = sorted([f.stem for f in components_dir.glob("*.q")])

        # Calculate cache hit rate
        total_requests = self.stats['cache_hits'] + self.stats['cache_misses']
        cache_hit_rate = (self.stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0

        # Server uptime info
        import time
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Quantum Server Status</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    max-width: 1000px;
                    margin: 50px auto;
                    padding: 20px;
                    background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
                    color: white;
                }}
                .container {{
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 15px;
                    padding: 40px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                }}
                h1 {{ margin-top: 0; font-size: 2.5em; }}
                .status-badge {{
                    display: inline-block;
                    background: #2ecc71;
                    color: white;
                    padding: 8px 20px;
                    border-radius: 20px;
                    font-weight: bold;
                    margin-left: 10px;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin: 30px 0;
                }}
                .stat-card {{
                    background: rgba(255, 255, 255, 0.15);
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                }}
                .stat-value {{
                    font-size: 2.5em;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                .stat-label {{
                    font-size: 0.9em;
                    opacity: 0.9;
                }}
                .box {{
                    background: rgba(255, 255, 255, 0.1);
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                }}
                .component-list {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                    gap: 10px;
                    margin-top: 15px;
                }}
                .component-item {{
                    background: rgba(255, 255, 255, 0.2);
                    padding: 10px;
                    border-radius: 5px;
                    text-align: center;
                }}
                .component-item a {{
                    color: white;
                    text-decoration: none;
                    font-weight: 500;
                }}
                .component-item a:hover {{
                    text-decoration: underline;
                }}
                code {{
                    background: rgba(0, 0, 0, 0.3);
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                }}
                .progress-bar {{
                    background: rgba(255, 255, 255, 0.2);
                    border-radius: 10px;
                    height: 30px;
                    overflow: hidden;
                    margin-top: 10px;
                }}
                .progress-fill {{
                    background: linear-gradient(90deg, #3498db, #2ecc71);
                    height: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    transition: width 0.3s ease;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ Quantum Server Status <span class="status-badge">OPERATIONAL</span></h1>
                <p><strong>Server Time:</strong> {current_time}</p>

                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-label">Components Served</div>
                        <div class="stat-value">{self.stats['components_served']}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Cache Hits</div>
                        <div class="stat-value">{self.stats['cache_hits']}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Cache Misses</div>
                        <div class="stat-value">{self.stats['cache_misses']}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Cache Hit Rate</div>
                        <div class="stat-value">{cache_hit_rate:.1f}%</div>
                    </div>
                </div>

                <div class="box">
                    <h2>📊 Cache Performance</h2>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {cache_hit_rate}%">
                            {cache_hit_rate:.1f}%
                        </div>
                    </div>
                    <p style="margin-top: 10px; font-size: 0.9em;">
                        Cache is {'enabled' if self.config['performance']['cache_templates'] else 'disabled'}
                    </p>
                </div>

                <div class="box">
                    <h2>⚙️ Server Configuration</h2>
                    <ul style="list-style: none; padding: 0;">
                        <li>🌐 <strong>Port:</strong> <code>{self.config['server']['port']}</code></li>
                        <li>📂 <strong>Components Directory:</strong> <code>{self.config['paths']['components']}</code></li>
                        <li>🐛 <strong>Debug Mode:</strong> <code>{self.config['server']['debug']}</code></li>
                        <li>🔄 <strong>Auto-reload:</strong> <code>{self.config['server']['reload']}</code></li>
                        <li>💾 <strong>Cache Enabled:</strong> <code>{self.config['performance']['cache_templates']}</code></li>
                    </ul>
                </div>

                <div class="box">
                    <h2>📦 Available Components ({len(available_components)})</h2>
                    {f'''
                    <div class="component-list">
                        {''.join([f'<div class="component-item"><a href="/{comp}">{comp}</a></div>' for comp in available_components])}
                    </div>
                    ''' if available_components else '<p>No components found in components directory.</p>'}
                </div>

                <div class="box">
                    <h2>🔗 Useful Links</h2>
                    <ul>
                        <li><a href="/" style="color: white;">Home Page</a></li>
                        <li><a href="/_health" style="color: white;">Refresh Status</a></li>
                        <li><a href="/static" style="color: white;">Static Files</a></li>
                    </ul>
                </div>

                <div style="text-align: center; margin-top: 30px; opacity: 0.8;">
                    <p>✨ Quantum Framework - All systems operational</p>
                </div>
            </div>

            <script>
                // Auto-refresh every 30 seconds
                setTimeout(() => location.reload(), 30000);
            </script>
        </body>
        </html>
        """

        return Response(html, mimetype='text/html')

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


    def _find_action_in_component(self, ast) -> Optional[ActionNode]:
        """
        Find q:action statement in component AST.

        Args:
            ast: Component AST

        Returns:
            ActionNode if found, None otherwise
        """
        # Check if component has statements
        if not hasattr(ast, 'statements'):
            return None

        # Look for ActionNode in statements
        for statement in ast.statements:
            if isinstance(statement, ActionNode):
                return statement

        return None


    def _print_banner(self):
        """Print startup banner with server information"""
        port = self.config['server']['port']
        host = self.config['server']['host']
        components_dir = self.config['paths']['components']

        # Check for components
        comp_dir_path = Path(components_dir)
        available_components = []
        if comp_dir_path.exists():
            available_components = list(comp_dir_path.glob("*.q"))

        print("\n" + "="*60)
        print("🚀 QUANTUM WEB SERVER")
        print("="*60)
        print(f"📡 Server URL:      http://localhost:{port}")
        print(f"📊 Status Page:     http://localhost:{port}/_health")
        print(f"📂 Components:      {components_dir}")
        print(f"📦 Available:       {len(available_components)} component(s)")
        print(f"🔄 Auto-reload:     {self.config['server']['reload']}")
        print(f"🐛 Debug mode:      {self.config['server']['debug']}")
        print(f"💾 Cache enabled:   {self.config['performance']['cache_templates']}")
        print("="*60)
        print("✅ ALL SYSTEMS LOADED SUCCESSFULLY")
        print("="*60)
        print("✨ Magic is happening... Press Ctrl+C to stop")
        print(f"💡 Visit http://localhost:{port}/_health to see server status")
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
