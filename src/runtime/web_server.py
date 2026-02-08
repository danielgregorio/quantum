"""
Quantum Web Server - Serves .q components as HTML pages

ColdFusion-style simplicity: Just run `quantum start` and it works! 🪄
"""

import sys
import os
import re
import hashlib
import yaml
from pathlib import Path
from flask import Flask, Response, request, send_from_directory, render_template_string, session, redirect, abort
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
    Quantum Web Server - Magic happens here!

    Automatically serves .q files as HTML pages.
    No configuration needed (but you can customize via quantum.config.yaml)
    """

    def __init__(self, config_path: str = 'quantum.config.yaml', hot_reload: bool = False, hot_reload_port: int = None):
        """
        Initialize Quantum Web Server.

        Args:
            config_path: Path to configuration file
            hot_reload: Enable hot reload mode (inject client script)
            hot_reload_port: WebSocket port for hot reload
        """
        self.config = self._load_config(config_path)
        # Disable Flask's built-in static serving - we use our own serve_static route
        self.app = Flask(__name__, static_folder=None)

        # Hot reload configuration
        self.hot_reload_enabled = hot_reload
        self.hot_reload_port = hot_reload_port or 35729

        # Setup secret key for sessions (flash messages)
        # Use env var or config for stable key across Gunicorn workers
        self.app.secret_key = os.environ.get(
            'QUANTUM_SECRET_KEY',
            self.config.get('security', {}).get('secret_key', secrets.token_hex(32))
        )

        self.parser = QuantumParser()
        self.template_cache: Dict[str, Any] = {}  # AST cache
        self.action_handler = ActionHandler()

        # Phase F: Application scope (global state shared across all users)
        self.application_scope: Dict[str, Any] = {}

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
                    # Deep merge user config with defaults
                    for key, value in user_config.items():
                        if key in default_config and isinstance(default_config[key], dict) and isinstance(value, dict):
                            default_config[key].update(value)
                        else:
                            default_config[key] = value
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

        @self.app.route('/static/<path:filepath>')
        def serve_static(filepath):
            """Serve static files (CSS, JS, images)"""
            static_dir = self.config['paths']['static']
            # Convert relative path to absolute for send_from_directory
            if not os.path.isabs(static_dir):
                static_dir = os.path.abspath(static_dir)
            return send_from_directory(static_dir, filepath)

        @self.app.route('/<path:component_path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
        def dynamic_route(component_path):
            """Dynamically serve any .q component"""
            # Remove .q extension if provided
            if component_path.endswith('.q'):
                component_path = component_path[:-2]

            return self._serve_component(component_path)

        @self.app.route('/health')
        def health_check():
            """Health check endpoint for container orchestration."""
            import json
            return Response(
                json.dumps({
                    'status': 'healthy',
                    'service': 'quantum',
                    'version': '1.0.0'
                }),
                status=200,
                mimetype='application/json'
            )

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
                # For index route, show welcome page; for other routes, return 404
                if component_path == 'index':
                    return self._render_welcome_page()
                else:
                    abort(404)

        try:
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
            runtime = ComponentRuntime(config=self.config)
            runtime.execute_component(ast, params)

            # Phase F: Sync session back to Flask session
            session['quantum_session'] = runtime.execution_context.session_vars
            session.modified = True

            # Debug: log session state after execution
            if self.config['server']['debug'] and request.method == 'POST':
                import logging
                logger = logging.getLogger('quantum.debug')
                logger.warning(f"[DEBUG] POST form_data: {dict(request.form)}")
                logger.warning(f"[DEBUG] session_vars after exec: {runtime.execution_context.session_vars}")
                logger.warning(f"[DEBUG] app_vars keys: {list(runtime.execution_context.application_vars.keys())}")
                print(f"[DEBUG] POST form_data: {dict(request.form)}", flush=True)
                print(f"[DEBUG] session_vars after exec: {runtime.execution_context.session_vars}", flush=True)
                print(f"[DEBUG] app_vars keys: {list(runtime.execution_context.application_vars.keys())}", flush=True)

            # Render to HTML using runtime's execution context
            renderer = HTMLRenderer(runtime.execution_context)
            html = renderer.render(ast)

            # Phase B: For partial requests, return only component HTML
            if partial:
                return Response(html, mimetype='text/html')

            # For full page requests, add HTMX support
            if '<html' in html.lower():
                # Component already has full HTML structure - inject HTMX into it
                full_html = self._inject_htmx(html)
            else:
                # Fragment component - wrap with full page + HTMX
                full_html = self._wrap_with_htmx(html, component_path)

            # Extract inline CSS and JS to external files
            full_html = self._extract_inline_assets(full_html)

            # Pretty-print HTML for readable View Source
            full_html = self._prettify_html(full_html)

            return Response(full_html, mimetype='text/html')

        except QuantumParseError as e:
            # Enhanced parse error with context
            enhanced_error = ErrorHandler.handle_parse_error(e, component_path)

            if self.config['server']['debug']:
                # Show enhanced error in debug mode
                return self._render_error_page(
                    title="Parse Error",
                    message=f"Could not parse component: {component_path}",
                    details=str(enhanced_error),
                    suggestion="Check XML syntax and Quantum tag usage. Use 'quantum inspect {component_path}' for details."
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
                enhanced_error = ErrorHandler.handle_runtime_error(e, str(component_path), component_path)

                import traceback
                return self._render_error_page(
                    title="Runtime Error",
                    message=f"Error in component: {component_path}",
                    details=str(enhanced_error) + "\n\n" + traceback.format_exc(),
                    suggestion="Use 'quantum inspect {component_path}' to debug. Check component logic and data sources."
                ), 500
            else:
                # Generic error in production
                return self._render_error_page(
                    title="Error",
                    message="An error occurred",
                    details="Enable debug mode for more details.",
                    suggestion=""
                ), 500

    def _get_static_dir(self) -> str:
        """Resolve and ensure the static directory exists."""
        static_dir = self.config['paths']['static']
        if not os.path.isabs(static_dir):
            static_dir = os.path.abspath(static_dir)
        os.makedirs(static_dir, exist_ok=True)
        return static_dir

    def _extract_inline_assets(self, html: str) -> str:
        """
        Extract inline <style> and <script> blocks to external files.

        Replaces inline CSS with <link rel="stylesheet"> and inline JS
        (without src attribute) with <script src="...">.

        Args:
            html: Full HTML document string

        Returns:
            HTML with inline assets replaced by external file references
        """
        static_dir = self._get_static_dir()

        # --- Extract CSS ---
        style_pattern = re.compile(r'<style[^>]*>(.*?)</style>', re.DOTALL | re.IGNORECASE)
        css_matches = style_pattern.findall(html)

        if css_matches:
            all_css = '\n'.join(css_matches)
            css_hash = hashlib.md5(all_css.encode()).hexdigest()[:10]
            css_filename = f'styles-{css_hash}.css'
            css_path = os.path.join(static_dir, css_filename)

            if not os.path.exists(css_path):
                with open(css_path, 'w', encoding='utf-8') as f:
                    f.write(all_css)

            html = style_pattern.sub('', html)

            link_tag = f'<link rel="stylesheet" href="static/{css_filename}">'
            if '</head>' in html:
                html = html.replace('</head>', f'    {link_tag}\n  </head>', 1)
            elif '</HEAD>' in html:
                html = html.replace('</HEAD>', f'    {link_tag}\n  </HEAD>', 1)

        # --- Extract inline JS (skip <script src="..."> tags) ---
        script_pattern = re.compile(
            r'<script(?![^>]*\bsrc\b)[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE
        )
        js_matches = script_pattern.findall(html)

        if js_matches:
            all_js = '\n'.join(m.strip() for m in js_matches)
            js_hash = hashlib.md5(all_js.encode()).hexdigest()[:10]
            js_filename = f'scripts-{js_hash}.js'
            js_path = os.path.join(static_dir, js_filename)

            if not os.path.exists(js_path):
                with open(js_path, 'w', encoding='utf-8') as f:
                    f.write(all_js)

            html = script_pattern.sub('', html)

            script_tag = f'<script src="static/{js_filename}"></script>'
            if '</body>' in html:
                html = html.replace('</body>', f'    {script_tag}\n  </body>', 1)
            elif '</BODY>' in html:
                html = html.replace('</BODY>', f'    {script_tag}\n  </BODY>', 1)

        return html

    def _prettify_html(self, html: str) -> str:
        """
        Pretty-print HTML with indentation for readable View Source output.

        Adds newlines and 2-space indentation around block-level elements
        while preserving content inside whitespace-sensitive elements
        (<pre>, <textarea>) verbatim.

        Args:
            html: Full HTML document string

        Returns:
            Indented HTML string
        """
        BLOCK_ELEMENTS = {
            'html', 'head', 'body', 'header', 'footer', 'main', 'section',
            'nav', 'article', 'aside', 'div', 'ul', 'ol', 'li', 'table',
            'thead', 'tbody', 'tr', 'th', 'td', 'form', 'fieldset',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'blockquote',
            'figure', 'figcaption', 'details', 'summary',
            'title', 'script', 'style', 'noscript', 'template',
        }
        VOID_ELEMENTS = {
            'br', 'hr', 'img', 'input', 'meta', 'link', 'col', 'area',
            'base', 'embed', 'source', 'track', 'wbr',
        }
        INLINE_ELEMENTS = {
            'a', 'span', 'strong', 'em', 'b', 'i', 'u', 'small', 'sub',
            'sup', 'abbr', 'cite', 'code', 'label', 'button', 'select',
            'option', 'time', 'mark',
        }
        PRESERVE_ELEMENTS = {'pre', 'textarea'}

        # Tokenize: split into tags and text segments
        token_re = re.compile(r'(<[^>]+>)')
        tokens = token_re.split(html)

        tag_name_re = re.compile(r'^<\s*/?\s*([a-zA-Z][a-zA-Z0-9]*)', re.IGNORECASE)

        depth = 0
        output = []
        preserve_depth = 0

        def _at_line_start():
            """Check if we're at the start of a line (last output ends with newline or empty)."""
            return not output or output[-1].endswith('\n')

        for token in tokens:
            if not token:
                continue

            is_tag = token.startswith('<')

            if is_tag:
                tag_match = tag_name_re.match(token)
                tag_name = tag_match.group(1).lower() if tag_match else ''
                is_closing = token.startswith('</')
                is_self_closing = token.rstrip().endswith('/>')
                is_doctype = token.upper().startswith('<!DOCTYPE')
                is_comment = token.startswith('<!--')

                # Handle preserve elements
                if tag_name in PRESERVE_ELEMENTS:
                    if is_closing:
                        preserve_depth = max(preserve_depth - 1, 0)
                        output.append(token)
                        output.append('\n')
                    elif not is_self_closing:
                        preserve_depth += 1
                        indent = '  ' * depth
                        if not _at_line_start():
                            output.append('\n')
                        output.append(f'{indent}{token}')
                    else:
                        indent = '  ' * depth
                        output.append(f'{indent}{token}\n')
                    continue

                # Inside preserved content — output verbatim
                if preserve_depth > 0:
                    output.append(token)
                    continue

                if is_doctype or is_comment:
                    indent = '  ' * depth
                    if not _at_line_start():
                        output.append('\n')
                    output.append(f'{indent}{token}\n')
                elif tag_name in BLOCK_ELEMENTS:
                    if is_closing:
                        depth = max(depth - 1, 0)
                        indent = '  ' * depth
                        if not _at_line_start():
                            output.append('\n')
                        output.append(f'{indent}{token}\n')
                    elif is_self_closing:
                        indent = '  ' * depth
                        if not _at_line_start():
                            output.append('\n')
                        output.append(f'{indent}{token}\n')
                    else:
                        indent = '  ' * depth
                        if not _at_line_start():
                            output.append('\n')
                        output.append(f'{indent}{token}\n')
                        depth += 1
                elif tag_name in VOID_ELEMENTS:
                    indent = '  ' * depth
                    if not _at_line_start():
                        output.append('\n')
                    output.append(f'{indent}{token}\n')
                elif tag_name in INLINE_ELEMENTS:
                    # Inline elements stay on same line as surrounding content
                    if _at_line_start():
                        indent = '  ' * depth
                        output.append(f'{indent}{token}')
                    else:
                        output.append(token)
                else:
                    # Unknown tags — treat as inline
                    output.append(token)
            else:
                # Text node
                if preserve_depth > 0:
                    output.append(token)
                else:
                    stripped = token.strip()
                    if stripped:
                        if _at_line_start():
                            indent = '  ' * depth
                            output.append(f'{indent}{stripped}\n')
                        else:
                            output.append(stripped)

        result = ''.join(output)
        # Clean up multiple blank lines
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result.strip() + '\n'

    def _get_hot_reload_script(self) -> str:
        """
        Get the hot reload client script.

        Returns:
            JavaScript code for hot reload client
        """
        if not self.hot_reload_enabled:
            return ''

        return f"""
    <!-- Quantum Hot Reload Client -->
    <script>
    window.__QUANTUM_HOT_RELOAD_CONFIG = {{
        host: 'localhost',
        port: {self.hot_reload_port},
        enableLogging: true,
        enableToasts: true,
        preserveState: true
    }};
    </script>
    <script>
    (function() {{
        'use strict';
        var config = window.__QUANTUM_HOT_RELOAD_CONFIG || {{}};
        var WS_URL = 'ws://' + (config.host || 'localhost') + ':' + (config.port || 35729);
        var RECONNECT_INTERVAL = 1000;
        var MAX_RECONNECT_ATTEMPTS = 30;
        var socket = null;
        var reconnectAttempts = 0;
        var overlay = null;
        var isConnected = false;
        var preservedState = {{}};

        function log(msg) {{
            if (config.enableLogging !== false) console.log('[Hot Reload] ' + msg);
        }}

        function connect() {{
            if (socket && socket.readyState === WebSocket.OPEN) return;
            try {{
                socket = new WebSocket(WS_URL);
                socket.onopen = function() {{
                    log('Connected to dev server');
                    reconnectAttempts = 0;
                    isConnected = true;
                    hideOverlay();
                    showToast('Hot reload connected', 'success');
                }};
                socket.onclose = function() {{
                    isConnected = false;
                    log('Disconnected from dev server');
                    scheduleReconnect();
                }};
                socket.onerror = function() {{ log('WebSocket error'); }};
                socket.onmessage = function(e) {{
                    try {{ handleMessage(JSON.parse(e.data)); }} catch (err) {{}}
                }};
            }} catch (e) {{
                log('Failed to connect: ' + e);
                scheduleReconnect();
            }}
        }}

        function scheduleReconnect() {{
            if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {{
                showOverlay({{type: 'connection_lost', message: 'Lost connection to dev server. Restart with: quantum dev'}});
                return;
            }}
            reconnectAttempts++;
            setTimeout(connect, RECONNECT_INTERVAL);
        }}

        function handleMessage(data) {{
            if (data.type === 'reload') {{
                log('Reload: ' + data.reloadType);
                if (data.reloadType === 'css') {{
                    reloadCSS();
                    showToast('Styles updated', 'info');
                }} else {{
                    preserveState();
                    showToast('Reloading...', 'info');
                    setTimeout(function() {{ location.reload(); }}, 100);
                }}
            }} else if (data.type === 'error') {{
                showOverlay(data.error);
            }} else if (data.type === 'clear_error') {{
                hideOverlay();
            }}
        }}

        function reloadCSS() {{
            var links = document.querySelectorAll('link[rel="stylesheet"]');
            var ts = Date.now();
            links.forEach(function(l) {{ l.href = l.href.split('?')[0] + '?_hr=' + ts; }});
            log('CSS reloaded');
        }}

        function preserveState() {{
            preservedState = {{}};
            document.querySelectorAll('form').forEach(function(f, i) {{
                var id = f.id || 'form_' + i;
                preservedState[id] = {{}};
                f.querySelectorAll('input,textarea,select').forEach(function(inp) {{
                    if (inp.name) {{
                        preservedState[id][inp.name] = (inp.type === 'checkbox' || inp.type === 'radio') ? inp.checked : inp.value;
                    }}
                }});
            }});
            preservedState._scroll = {{x: window.scrollX, y: window.scrollY}};
            try {{ sessionStorage.setItem('__quantum_hr_state', JSON.stringify(preservedState)); }} catch(e) {{}}
        }}

        function restoreState() {{
            try {{
                var s = sessionStorage.getItem('__quantum_hr_state');
                if (!s) return;
                var state = JSON.parse(s);
                sessionStorage.removeItem('__quantum_hr_state');
                Object.keys(state).forEach(function(fid) {{
                    if (fid.startsWith('_')) return;
                    var form = document.getElementById(fid) || document.forms[fid.replace('form_', '')];
                    if (!form) return;
                    Object.keys(state[fid]).forEach(function(n) {{
                        var inp = form.querySelector('[name="' + n + '"]');
                        if (inp) {{
                            if (inp.type === 'checkbox' || inp.type === 'radio') inp.checked = state[fid][n];
                            else inp.value = state[fid][n];
                        }}
                    }});
                }});
                if (state._scroll) setTimeout(function() {{ window.scrollTo(state._scroll.x, state._scroll.y); }}, 100);
            }} catch(e) {{}}
        }}

        function showOverlay(err) {{
            hideOverlay();
            overlay = document.createElement('div');
            overlay.id = '__quantum_hr_overlay';
            overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.9);z-index:999999;display:flex;align-items:center;justify-content:center;font-family:system-ui,sans-serif;';
            var c = document.createElement('div');
            c.style.cssText = 'max-width:800px;padding:40px;background:#1e1e1e;border-radius:8px;color:#fff;';
            var titleColor = err.type === 'connection_lost' ? '#ffc107' : '#f44336';
            c.innerHTML = '<h2 style="color:' + titleColor + ';margin:0 0 16px;">' + (err.type === 'connection_lost' ? 'Connection Lost' : 'Parse Error') + '</h2>' +
                (err.file ? '<p style="color:#888;margin:0 0 12px;font-size:14px;">File: ' + err.file + '</p>' : '') +
                '<pre style="background:#2d2d2d;padding:16px;border-radius:4px;overflow:auto;max-height:400px;color:#ff6b6b;white-space:pre-wrap;">' + escapeHtml(err.message) + '</pre>' +
                '<p style="color:#888;margin:16px 0 0;font-size:13px;">Fix the error and save to reload.</p>';
            overlay.appendChild(c);
            document.body.appendChild(overlay);
            overlay.onclick = function(e) {{ if (e.target === overlay) hideOverlay(); }};
        }}

        function hideOverlay() {{
            if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
            overlay = null;
        }}

        function showToast(msg, type) {{
            if (config.enableToasts === false) return;
            var old = document.getElementById('__quantum_hr_toast');
            if (old) old.parentNode.removeChild(old);
            var t = document.createElement('div');
            t.id = '__quantum_hr_toast';
            var bg = {{success:'#4caf50',error:'#f44336',warning:'#ff9800',info:'#2196f3'}}[type] || '#2196f3';
            t.style.cssText = 'position:fixed;bottom:20px;right:20px;padding:12px 20px;background:' + bg + ';color:#fff;border-radius:4px;font-family:system-ui;font-size:14px;z-index:999998;box-shadow:0 2px 8px rgba(0,0,0,0.2);';
            t.textContent = msg;
            document.body.appendChild(t);
            setTimeout(function() {{ if (t.parentNode) {{ t.style.opacity = '0'; t.style.transition = 'opacity 0.3s'; setTimeout(function() {{ if (t.parentNode) t.parentNode.removeChild(t); }}, 300); }} }}, 2000);
        }}

        function escapeHtml(text) {{
            var d = document.createElement('div');
            d.textContent = text;
            return d.innerHTML;
        }}

        setInterval(function() {{
            if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({{type:'ping'}}));
        }}, 30000);

        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', function() {{ restoreState(); connect(); }});
        }} else {{
            restoreState(); connect();
        }}
    }})();
    </script>"""

    def _inject_htmx(self, html: str) -> str:
        """
        Inject HTMX scripts into an existing full HTML document.

        Used when the component already renders a complete HTML page
        (e.g. type="page" components), to avoid double-wrapping.

        Args:
            html: Full HTML document string

        Returns:
            HTML document with HTMX script and config injected
        """
        htmx_head = '\n    <script src="https://unpkg.com/htmx.org@1.9.10"></script>'

        htmx_body = """
    <script>
        htmx.config.defaultSwapStyle = "innerHTML";
        htmx.config.defaultSwapDelay = 0;
        htmx.config.historyCacheSize = 10;
        if (window.location.hostname === 'localhost') {
            htmx.logAll();
        }
    </script>"""

        # Add hot reload script if enabled
        hot_reload_script = self._get_hot_reload_script()

        # Inject HTMX library before </head>
        if '</head>' in html:
            html = html.replace('</head>', htmx_head + '\n  </head>', 1)
        elif '</HEAD>' in html:
            html = html.replace('</HEAD>', htmx_head + '\n  </HEAD>', 1)

        # Inject HTMX config and hot reload script before </body>
        scripts = htmx_body + hot_reload_script
        if '</body>' in html:
            html = html.replace('</body>', scripts + '\n  </body>', 1)
        elif '</BODY>' in html:
            html = html.replace('</BODY>', scripts + '\n  </BODY>', 1)

        # Ensure DOCTYPE is present
        if not html.strip().lower().startswith('<!doctype'):
            html = '<!DOCTYPE html>\n' + html

        return html

    def _wrap_with_htmx(self, html: str, component_path: str) -> str:
        """
        Wrap component HTML with HTMX library support (Phase B).

        Adds:
        - HTMX library from CDN
        - Minimal CSS reset
        - HTMX configuration
        - Hot reload client (when enabled)

        Args:
            html: Rendered component HTML
            component_path: Component name for title

        Returns:
            Full HTML page with HTMX support
        """
        hot_reload_script = self._get_hot_reload_script()

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{component_path} - Quantum</title>

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
    {hot_reload_script}
</body>
</html>"""

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
                        <li>Debug mode: <code>{self.config['server'].get('debug', False)}</code></li>
                        <li>Auto-reload: <code>{self.config['server'].get('reload', False)}</code></li>
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

        print("\n" + "="*60)
        print("QUANTUM WEB SERVER")
        print("="*60)
        print(f"Server URL:      http://localhost:{port}")
        print(f"Components:      {components_dir}")
        print(f"Auto-reload:     {self.config['server'].get('reload', False)}")
        print(f"Debug mode:      {self.config['server'].get('debug', False)}")
        if self.hot_reload_enabled:
            print(f"Hot Reload:      ws://localhost:{self.hot_reload_port}")
        print("="*60)
        print("Press Ctrl+C to stop")
        print("="*60 + "\n")


    def start(self):
        """Start the Quantum web server"""
        host = self.config['server']['host']
        port = self.config['server']['port']
        debug = self.config['server'].get('debug', False)
        reload = self.config['server'].get('reload', False)

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
def start_server(
    config_path: str = 'quantum.config.yaml',
    port: int = None,
    hot_reload: bool = False,
    hot_reload_port: int = None
):
    """
    Start Quantum web server.

    Args:
        config_path: Path to configuration file
        port: Override port from config (optional)
        hot_reload: Enable hot reload mode
        hot_reload_port: WebSocket port for hot reload
    """
    server = QuantumWebServer(
        config_path,
        hot_reload=hot_reload,
        hot_reload_port=hot_reload_port
    )

    # Override port if specified
    if port is not None:
        server.config['server']['port'] = port

    server.start()


def create_app(config_path: str = 'quantum.config.yaml') -> Flask:
    """
    Application factory for Gunicorn/WSGI deployment.

    Usage with Gunicorn:
        gunicorn 'src.runtime.web_server:create_app()'

    Args:
        config_path: Path to configuration file

    Returns:
        Flask application instance
    """
    server = QuantumWebServer(config_path)
    return server.app


if __name__ == '__main__':
    start_server()
