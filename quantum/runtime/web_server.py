"""
Quantum Web Server - Serves .q components as HTML pages

ColdFusion-style simplicity: Just run `quantum start` and it works! 🪄
"""

import sys
import os
import re
import signal
import socket
import time
import hashlib
import yaml
import logging
from pathlib import Path
from flask import Flask, Response, request, send_from_directory, render_template_string, session, redirect, abort
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import secrets

# Fix imports

from quantum.core.parser import QuantumParser, QuantumParseError
from quantum.core.ast_nodes import ActionNode
from quantum.runtime.component import ComponentRuntime
from quantum.runtime.renderer import HTMLRenderer
from quantum.runtime.execution_context import ExecutionContext
from quantum.runtime.action_handler import ActionHandler
from quantum.runtime.auth_service import AuthService, AuthorizationError
from quantum.runtime.error_handler import ErrorHandler, QuantumError
# Imported lazily in methods to avoid circular import via runtime/__init__.py
_logging_setup = None

def _get_logging_setup():
    global _logging_setup
    if _logging_setup is None:
        from quantum.runtime import logging_setup as _mod
        _logging_setup = _mod
    return _logging_setup


@dataclass
class DynamicRoute:
    """A file-based route containing [param] segments."""
    pattern: re.Pattern
    file_path: Path
    param_names: List[str]
    static_segment_count: int



class ConfigError(Exception):
    """quantum.config.yaml is unreadable or invalid."""


# Top-level sections the engine understands. A typo like `servr:` used to be
# accepted in silence, so the whole section was ignored.
_KNOWN_SECTIONS = {
    'server', 'paths', 'defaults', 'datasources', 'database', 'llm',
    'performance', 'security', 'logging', 'development', 'deploy',
    'components', 'jobs', 'messaging',
}

# (section, key) -> expected python type(s)
_TYPED = {
    ('server', 'port'): int,
    ('server', 'host'): str,
    ('server', 'debug'): bool,
    ('server', 'reload'): bool,
    ('security', 'python_scripting'): bool,
    ('security', 'max_content_length'): int,
    ('llm', 'timeout'): int,
    ('llm', 'base_url'): str,
}


def _validate_config(config: dict, source: str) -> None:
    """Fail fast on a bad config instead of at the first request.

    `port: oitenta` used to be accepted and blew up much later inside
    app.run(); a datasource with no driver failed only when a query ran. The
    boot is where an operator is watching, so that is where it should break.
    """
    log = logging.getLogger('quantum')
    problems = []

    for section, key in _TYPED:
        block = config.get(section)
        if not isinstance(block, dict) or key not in block:
            continue
        value = block[key]
        expected = _TYPED[(section, key)]
        # bool is a subclass of int; check it first so True does not pass as a port
        if expected is int and isinstance(value, bool):
            problems.append(f"{section}.{key}: expected a number, got {value!r}")
        elif not isinstance(value, expected):
            problems.append(
                f"{section}.{key}: expected {expected.__name__}, got "
                f"{type(value).__name__} ({value!r})"
            )

    for name, ds in (config.get('datasources') or {}).items():
        if not isinstance(ds, dict):
            problems.append(f"datasources.{name}: expected a mapping")
            continue
        if not ds.get('driver'):
            problems.append(
                f"datasources.{name}: missing 'driver' (sqlite, postgresql, mysql)"
            )
        if not ds.get('database'):
            problems.append(f"datasources.{name}: missing 'database'")

    if problems:
        bullet = "\n  - "
        raise ConfigError(
            f"{source} has {len(problems)} problem(s):"
            + bullet + bullet.join(problems)
        )

    # Unknown sections are a warning, not an error: a newer config read by an
    # older engine is a real situation, and refusing to boot over it would be
    # worse than saying so.
    unknown = [k for k in config if k not in _KNOWN_SECTIONS]
    if unknown:
        log.warning(
            "%s has unrecognised top-level section(s): %s. They are ignored — "
            "check for a typo.", source, ', '.join(sorted(unknown))
        )


class QuantumWebServer:
    """
    Quantum Web Server - Magic happens here!

    Automatically serves .q files as HTML pages.
    No configuration needed (but you can customize via quantum.config.yaml)
    """

    PID_FILE = '.quantum.pid'

    def __init__(self, config_path: str = 'quantum.config.yaml', hot_reload: bool = False, hot_reload_port: int = None):
        """
        Initialize Quantum Web Server.

        Args:
            config_path: Path to configuration file
            hot_reload: Enable hot reload mode (inject client script)
            hot_reload_port: WebSocket port for hot reload
        """
        self._start_time = time.monotonic()
        self.config = self._load_config(config_path)
        self.logger = _get_logging_setup().setup_logging(self.config)

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
        # The runtime that executes q:action bodies needs the same config as
        # the page render. Built with no config, it could not see the
        # datasources declared in quantum.config.yaml: every q:query inside a
        # q:action failed with "Datasource 'db' is not declared locally" —
        # a form that writes to the database did not work at all.
        self.action_handler = ActionHandler(ComponentRuntime(config=self.config))

        # Phase F: Application scope (global state shared across all users)
        self.application_scope: Dict[str, Any] = {}

        # Setup routes
        self._setup_routes()
        self._setup_request_hooks()

        # Build dynamic route table for [param] segments
        self._dynamic_routes: List[DynamicRoute] = []
        self._build_dynamic_routes()


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
                # Loopback and no debugger by default. The old defaults were
                # host 0.0.0.0 + debug True, which put the Werkzeug interactive
                # debugger — an eval console — on every network interface: RCE
                # over the LAN from an unauthenticated browser tab, on the very
                # first `quantum start`. Binding wider or turning the debugger
                # on is now an explicit choice in quantum.config.yaml, and
                # start() refuses the dangerous combination (see _guard_debug).
                'host': '127.0.0.1',
                'reload': True,
                'debug': False
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
                # Do NOT fall back to defaults. This used to log a warning and
                # carry on, which meant a single typo in quantum.config.yaml
                # silently discarded the operator's datasources, host binding
                # and security settings and ran the server on defaults — the
                # exact opposite of what they configured, with one WARNING
                # line as the only sign.
                raise ConfigError(
                    f"could not read {config_path}: {e}\n"
                    f"Fix the file, or move it aside to run on defaults "
                    f"deliberately."
                )

        _validate_config(default_config, config_path)
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


    def _setup_request_hooks(self):
        """Setup before/after request hooks for request logging."""
        server_logger = logging.getLogger('quantum.server')

        @self.app.before_request
        def before_request_hook():
            request._quantum_start = time.monotonic()

        @self.app.after_request
        def after_request_hook(response):
            start = getattr(request, '_quantum_start', None)
            if start is not None:
                duration_ms = (time.monotonic() - start) * 1000
                _ls = _get_logging_setup()
                color = _ls.get_status_color(response.status_code)
                reset = _ls.get_reset()
                server_logger.info(
                    f"{request.method} {request.path} "
                    f"{color}{response.status_code}{reset} "
                    f"{duration_ms:.0f}ms"
                )
            return response

    def _build_dynamic_routes(self) -> None:
        """Scan components directory for files with [param] segments and build regex routes."""
        components_dir = Path(self.config['paths']['components'])
        if not components_dir.is_dir():
            return

        routes = []
        for q_file in components_dir.rglob('*.q'):
            rel = q_file.relative_to(components_dir)
            rel_str = str(rel).replace('\\', '/')

            # Only process files whose path contains a [param] segment
            if '[' not in rel_str:
                continue

            # Strip .q extension
            route_path = rel_str[:-2]  # remove '.q'

            # Strip trailing /index for directory-index style dynamic routes
            if route_path.endswith('/index'):
                route_path = route_path[:-6]

            # Extract param names and build regex
            parts = route_path.split('/')
            param_names = []
            regex_parts = []
            static_count = 0

            for part in parts:
                # Catch-all: [...param] captures remaining path segments
                m_catchall = re.fullmatch(r'\[\.\.\.(\w+)\]', part)
                # Single segment: [param]
                m = re.fullmatch(r'\[(\w+)\]', part)
                if m_catchall:
                    param_names.append(m_catchall.group(1))
                    regex_parts.append(f'(?P<{m_catchall.group(1)}>.+)')
                elif m:
                    param_names.append(m.group(1))
                    regex_parts.append(f'(?P<{m.group(1)}>[^/]+)')
                else:
                    static_count += 1
                    regex_parts.append(re.escape(part))

            pattern = re.compile('^' + '/'.join(regex_parts) + '$')
            routes.append(DynamicRoute(
                pattern=pattern,
                file_path=q_file,
                param_names=param_names,
                static_segment_count=static_count,
            ))

        # Sort: more static segments = higher priority (checked first)
        routes.sort(key=lambda r: -r.static_segment_count)
        self._dynamic_routes = routes

    def _match_dynamic_route(self, component_path: str):
        """Try to match a component path against dynamic routes.

        Returns:
            Tuple of (file_path, params_dict) or (None, {})
        """
        for route in self._dynamic_routes:
            m = route.pattern.match(component_path)
            if m:
                return route.file_path, m.groupdict()
        return None, {}

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

        # Containment check BEFORE touching the filesystem. `component_path`
        # comes straight from the URL, and Flask only normalises `..` for
        # clients that send a normalised path — a raw socket or
        # `curl --path-as-is` sends `GET /../../x` verbatim, and Werkzeug
        # passes the literal `..` through. Without this, GET /../../pwned
        # resolved to a .q two directories above the web root and executed it;
        # since a .q can carry <q:python>, that is unauthenticated RCE on the
        # default config (host 0.0.0.0, python_scripting on). Reproduced via
        # raw socket before adding this. See test_path_traversal.py.
        if not self._is_within_components(component_path):
            abort(404)

        file_path = Path(components_dir) / f'{component_path}.q'
        path_params = {}

        # Resolution priority:
        # 1. Exact match: components/admin/app/blog.q
        # 2. Directory index: components/admin/app/blog/index.q
        # 3. Dynamic segment: components/admin/app/[name].q
        # 4. 404
        if not file_path.exists():
            # Try index.q in subdirectory
            index_path = Path(components_dir) / component_path / 'index.q'
            if index_path.exists():
                file_path = index_path
            else:
                # Try dynamic route matching
                dyn_file, dyn_params = self._match_dynamic_route(component_path)
                if dyn_file:
                    file_path = dyn_file
                    path_params = dyn_params
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
            if getattr(ast, 'require_auth', False):
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
                    if status_code >= 400:
                        # A real error occurred in the action body. Report it as
                        # an actual error response instead of a redirect
                        # disguised as one (a 500 with a Location header reads
                        # as success to most clients).
                        return Response(
                            f"<h1>{status_code} Error</h1><p>The action could not be completed. Check server logs for details.</p>",
                            status=status_code,
                            mimetype='text/html'
                        )
                    # If no redirect and no error, fall through to render component

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

            # Inject dynamic route path parameters (e.g. [name] -> name="blog")
            if path_params:
                params['path_params'] = path_params
                for key, value in path_params.items():
                    params[key] = value

            # Execute component (runs queries, loops, functions, etc.)
            runtime = ComponentRuntime(config=self.config)
            runtime.execute_component(ast, params)

            # Phase F: Sync session back to Flask session
            session['quantum_session'] = runtime.execution_context.session_vars
            session.modified = True

            # Debug: log session state after execution
            if self.config['server']['debug'] and request.method == 'POST':
                debug_logger = logging.getLogger('quantum.runtime')
                debug_logger.debug(f"POST form_data: {dict(request.form)}")
                debug_logger.debug(f"session_vars after exec: {runtime.execution_context.session_vars}")
                debug_logger.debug(f"app_vars keys: {list(runtime.execution_context.application_vars.keys())}")

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

            # Root-relative on purpose. A bare "static/..." is resolved
            # against the current path, so a page at /admin/projects asked for
            # /admin/static/... and rendered with no CSS at all — silently,
            # since a 404 on a stylesheet does not fail the page.
            link_tag = f'<link rel="stylesheet" href="/static/{css_filename}">'
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

            # Root-relative — same reason as the stylesheet above.
            script_tag = f'<script src="/static/{js_filename}"></script>'
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

    # Attributes and API calls that mean a page actually needs htmx. Kept
    # deliberately broad — injecting an unused script is wasteful, but failing
    # to inject a needed one breaks the page, so ambiguity favours injecting.
    _HTMX_MARKERS = ('hx-', 'data-hx-', 'htmx.')

    def _needs_htmx(self, html: str) -> bool:
        """Whether this page uses htmx at all.

        Every served page used to get `<script src="https://unpkg.com/...">`
        unconditionally. Measured across the repo: 5 of 268 .q files carry an
        htmx marker, so 98% of pages pulled a third-party CDN dependency they
        never touched — a runtime network requirement for an offline or
        homelab deployment, which is the audience the project declares
        (FRAMEWORK_PLAN Fase 0.3), and a script a restrictive CSP blocks
        outright.

        A handful of other components (htmx_counter.q, htmx_click.q,
        htmx_add_todo.q) are htmx TARGETS — fragments returned into a page
        that drives them — and carry no markers of their own. They are served
        as partials, which never got the injection either way.
        """
        return any(marker in html for marker in self._HTMX_MARKERS)

    def _inject_htmx(self, html: str) -> str:
        """
        Inject HTMX scripts into an existing full HTML document.

        Used when the component already renders a complete HTML page
        (e.g. type="page" components), to avoid double-wrapping.

        Args:
            html: Full HTML document string

        Returns:
            HTML document with HTMX script and config injected, or unchanged
            when the page does not use htmx.
        """
        if not self._needs_htmx(html):
            # Still inject hot reload, which is independent of htmx.
            return self._inject_scripts_only(html, self._get_hot_reload_script())

        htmx_head = f'\n    <script src="{self._htmx_url()}"></script>'

        # Guarded: this used to call htmx.config directly, so a CDN that was
        # slow, blocked or offline turned into "htmx is not defined" on every
        # page — an error about the framework's own injected script, in an app
        # that may not use htmx at all.
        htmx_body = """
    <script>
        if (window.htmx) {
            htmx.config.defaultSwapStyle = "innerHTML";
            htmx.config.defaultSwapDelay = 0;
            htmx.config.historyCacheSize = 10;
            if (window.location.hostname === 'localhost') {
                htmx.logAll();
            }
        } else {
            console.warn('Quantum: this page uses htmx but the library did not load.');
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
        return self._inject_scripts_only(html, htmx_body + hot_reload_script)

    def _htmx_url(self) -> str:
        """Where to load htmx from.

        Prefers a vendored copy at static/vendor/htmx.min.js so an offline or
        air-gapped deployment works; falls back to the CDN. Vendoring the file
        is the remaining half of this fix — see DOGFOOD_NOTES.md item 8.
        """
        vendored = Path(self.config['paths']['static']) / 'vendor' / 'htmx.min.js'
        if vendored.is_file():
            return '/static/vendor/htmx.min.js'
        return self.config.get('server', {}).get(
            'htmx_url', 'https://unpkg.com/htmx.org@1.9.10'
        )

    def _inject_scripts_only(self, html: str, scripts: str) -> str:
        """Append scripts before </body> and guarantee a DOCTYPE."""
        if scripts:
            if '</body>' in html:
                html = html.replace('</body>', scripts + '\n  </body>', 1)
            elif '</BODY>' in html:
                html = html.replace('</BODY>', scripts + '\n  </BODY>', 1)

        # Ensure DOCTYPE is present. A .q cannot emit one itself — a DOCTYPE is
        # only valid before the root element, and the root element is
        # <q:component>. See DOGFOOD_NOTES.md item 4.
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

        # Only when the fragment actually uses htmx — see _needs_htmx().
        #
        # The config block is emitted with the tag, not independently. Making
        # only the <script src> conditional left `htmx.config...` running on
        # every page with the library absent, which turned a page that merely
        # did not use htmx into a page that threw "htmx is not defined" — a
        # regression this path introduced and the full-document path did not,
        # because only that one had been examined.
        uses_htmx = self._needs_htmx(html)
        htmx_tag = (f'<script src="{self._htmx_url()}"></script>'
                    if uses_htmx else '')
        htmx_config = """<script>
        if (window.htmx) {
            htmx.config.defaultSwapStyle = "innerHTML";
            htmx.config.defaultSwapDelay = 0;
            htmx.config.historyCacheSize = 10;
            if (window.location.hostname === 'localhost') {
                htmx.logAll();
            }
        } else {
            console.warn('Quantum: this page uses htmx but the library did not load.');
        }
    </script>""" if uses_htmx else ''

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{component_path} - Quantum</title>

    {htmx_tag}

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

    {htmx_config}
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

        When a form submits a hidden field named 'action' with the action name,
        this method matches it to the correct ActionNode. If no 'action' field
        is provided or no match is found, falls back to the first ActionNode.

        Args:
            ast: Component AST

        Returns:
            ActionNode if found, None otherwise
        """
        # Check if component has statements
        if not hasattr(ast, 'statements'):
            return None

        # Collect all ActionNodes
        action_nodes = [s for s in ast.statements if isinstance(s, ActionNode)]

        if not action_nodes:
            return None

        # If only one action, return it directly
        if len(action_nodes) == 1:
            return action_nodes[0]

        # Multiple actions: match by 'action' form field
        requested_action = request.form.get('action', '')
        if requested_action:
            for node in action_nodes:
                if getattr(node, 'name', '') == requested_action:
                    return node

        # Fallback to first action
        return action_nodes[0]


    def _count_component_files(self) -> int:
        """Count .q files in the components directory."""
        components_dir = Path(self.config['paths']['components'])
        if not components_dir.is_dir():
            return 0
        return sum(1 for _ in components_dir.rglob('*.q'))

    def _count_routes(self):
        """Return (static_count, dynamic_count) of registered routes."""
        static_count = len([r for r in self.app.url_map.iter_rules()
                           if '<' not in str(r)])
        dynamic_count = len(self._dynamic_routes)
        return static_count, dynamic_count

    def _print_banner(self):
        """Print startup banner with server information."""
        port = self.config['server']['port']
        components_dir = self.config['paths']['components']
        log_config = self.config.get('logging', {})
        startup_ms = (time.monotonic() - self._start_time) * 1000
        file_count = self._count_component_files()
        static_routes, dynamic_routes = self._count_routes()

        print()
        print("=" * 60)
        print("  QUANTUM WEB SERVER")
        print("=" * 60)
        print(f"  URL:             http://localhost:{port}")
        print(f"  Components:      {components_dir} ({file_count} files)")
        print(f"  Routes:          {static_routes} static + {dynamic_routes} dynamic")
        print(f"  Log level:       {log_config.get('level', 'INFO')}")
        if log_config.get('file', True):
            print(f"  Log file:        {log_config.get('filename', 'quantum.log')}")
        print(f"  Auto-reload:     {self.config['server'].get('reload', False)}")
        print(f"  Debug mode:      {self.config['server'].get('debug', False)}")
        if self.hot_reload_enabled:
            print(f"  Hot Reload:      ws://localhost:{self.hot_reload_port}")
        print(f"  Startup time:    {startup_ms:.0f}ms")
        print("=" * 60)
        print("  Press Ctrl+C to stop")
        print("=" * 60)
        print()

    def _is_within_components(self, component_path: str) -> bool:
        """True only if `<components_dir>/<component_path>.q` stays inside the
        components directory after resolving `..`, symlinks and separators.

        Also guards the index.q and dynamic-route lookups, since both derive
        their path from the same untrusted `component_path`.
        """
        # Reject the obvious traversal tokens outright — cheaper than resolving,
        # and covers the raw-socket `..` and backslash cases on Windows.
        if '..' in component_path.replace('\\', '/').split('/'):
            return False
        try:
            root = Path(self.config['paths']['components']).resolve()
            target = (root / f'{component_path}.q').resolve()
        except (OSError, ValueError, RuntimeError):
            return False
        # Python 3.9+: is_relative_to. The candidate must sit under the root.
        return target == root or root in target.parents

    def _check_port_available(self, host: str, port: int) -> bool:
        """Check if a port is available for binding."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1' if host == '0.0.0.0' else host, port))
                return result != 0  # 0 means connection succeeded → port in use
        except OSError:
            return True  # If we can't connect, assume port is free

    def _write_pid_file(self, is_reloader_child: bool = False):
        """Write .quantum.pid: this process, plus the parent under the reloader.

        With `reload: true` Werkzeug serves from a CHILD process. Recording
        only the parent meant `quantum stop` killed the parent and left the
        child listening on the port. `quantum stop` reads every line.
        """
        pids = [os.getppid(), os.getpid()] if is_reloader_child else [os.getpid()]
        try:
            Path(self.PID_FILE).write_text(
                '\n'.join(map(str, pids)) + '\n', encoding='utf-8')
        except OSError as e:
            self.logger.warning(f"Could not write PID file: {e}")

    def _remove_pid_file(self):
        """Remove .quantum.pid if it exists.

        Only the process that started the server owns the file. The reloader
        child exits with code 3 on EVERY code change to be restarted, and its
        cleanup used to delete the file — so after the first hot reload
        `quantum stop` reported "No running server found" while it was up.
        """
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            return
        try:
            Path(self.PID_FILE).unlink(missing_ok=True)
        except OSError:
            pass

    def _cleanup(self):
        """Cleanup on shutdown: remove PID file, log shutdown."""
        self._remove_pid_file()
        self.logger.info("Server stopped")

    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        def _handler(signum, frame):
            self._cleanup()
            sys.exit(0)

        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)
        # Windows-specific: CTRL_BREAK_EVENT
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, _handler)

    def start(self):
        """Start the Quantum web server."""
        host = self.config['server']['host']
        port = self.config['server']['port']
        debug = self.config['server'].get('debug', False)
        reload = self.config['server'].get('reload', False)

        # The Werkzeug debugger is an eval console. Never expose it on a
        # non-loopback interface, even if the config asks for it — that is
        # unauthenticated RCE over the network. Drop the debugger rather than
        # refusing to start, so a misconfiguration degrades safely.
        if debug and host not in ('127.0.0.1', 'localhost', '::1'):
            self.logger.error(
                f"Refusing to run the debugger (debug: true) on {host}: the "
                f"Werkzeug console would be an eval prompt open to the network. "
                f"Serving with the debugger OFF. Use host 127.0.0.1 for a local "
                f"debug session."
            )
            debug = False

        # Werkzeug's reloader re-executes this whole program in a child
        # process and sets WERKZEUG_RUN_MAIN in it. Without this guard the
        # child ran the port check, found the PARENT's own socket bound,
        # reported "port already in use" and returned — so `quantum start`
        # printed its success banner and then died, with nothing listening.
        # `reload: true` is the shipped default in quantum.config.yaml, which
        # means the documented way to start the server could not start it.
        is_reloader_child = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'

        if not is_reloader_child and not self._check_port_available(host, port):
            self.logger.error(
                f"Port {port} already in use. Stop the other process, or set "
                f"server.port in quantum.config.yaml."
            )
            # Non-zero: a supervisor, container healthcheck or CI step must be
            # able to tell a dead server from a live one. This used to return
            # None, so the CLI exited 0 while nothing was listening.
            return 1

        self._write_pid_file(is_reloader_child)
        self._register_signal_handlers()
        self._print_banner()

        try:
            self.app.run(
                host=host,
                port=port,
                debug=debug,
                use_reloader=reload
            )
        except KeyboardInterrupt:
            self.logger.info("Stopped by user")
        except OSError as e:
            # Losing the bind after the banner printed is the case most likely
            # to be mistaken for success.
            self.logger.error(f"Could not bind {host}:{port} — {e}")
            return 1
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            return 1
        finally:
            self._cleanup()
        return 0


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

    return server.start()


def create_app(config_path: str = 'quantum.config.yaml') -> Flask:
    """
    Application factory for a real WSGI server. This is the production path.

        gunicorn 'quantum.runtime.web_server:create_app()' \
            --bind 0.0.0.0:8080 --workers 4

    (The example here used to say `src.runtime.web_server`, the layout that
    stopped existing when src/ became the quantum/ package — so the one
    documented production entry point did not import.)

    `quantum start` runs Flask's DEVELOPMENT server: single-process, not
    hardened, and now bound to loopback by default. Use it while writing the
    app, not to serve it.

    Two things to set when you deploy behind gunicorn:

    - QUANTUM_SECRET_KEY, or security.secret_key in the config. Without it
      each worker generates its OWN random key at import, so a session cookie
      signed by one worker is rejected by the next and users are logged out at
      random.
    - server.host: 0.0.0.0 in the config if the container needs it. Leave
      server.debug false — the server refuses the debugger off loopback
      anyway, because it is an eval console.

    Args:
        config_path: Path to configuration file

    Returns:
        Flask application instance
    """
    server = QuantumWebServer(config_path)

    if not os.environ.get('QUANTUM_SECRET_KEY') and not (
        server.config.get('security', {}) or {}
    ).get('secret_key'):
        server.logger.warning(
            "No QUANTUM_SECRET_KEY and no security.secret_key: this worker "
            "generated a random session key at import. With more than one "
            "worker, session cookies signed by one are rejected by the others "
            "and users are logged out at random. Set one before serving."
        )

    return server.app


if __name__ == '__main__':
    start_server()
