"""
Quantum Web Server - Serves .q components as HTML pages

ColdFusion-style simplicity: Just run `quantum start` and it works! 🪄
"""

import os
from html import escape as html_escape
import re
import time
import logging
from pathlib import Path
from flask import Flask, Response, request, send_from_directory, session, redirect, abort
from flask.json.tag import JSONTag, TaggedJSONSerializer
from flask.sessions import SecureCookieSessionInterface
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import secrets

# Fix imports

from quantum.core.parser import QuantumParser, QuantumParseError
from quantum.core.ast_nodes import ActionNode
from werkzeug.exceptions import HTTPException
from quantum.runtime.component import ComponentRuntime
from quantum.runtime.executors.control_flow.redirect_executor import PageRedirect
from quantum.runtime.renderer import HTMLRenderer
from quantum.runtime.action_handler import ActionHandler
from quantum.runtime.auth_service import AuthService
from quantum.runtime.error_handler import ErrorHandler, QuantumError
from quantum.runtime.dev_panel import note as dev_note, note_scopes as dev_scopes
# Imported lazily in methods to avoid circular import via runtime/__init__.py
_logging_setup = None

from quantum.runtime.web_config import ConfigError, ConfigLoading, _validate_config  # noqa: E402,F401
from quantum.runtime.web_errors import ErrorPages  # noqa: E402
from quantum.runtime.web_html import HtmlPostProcessing  # noqa: E402
from quantum.runtime.web_lifecycle import ServerLifecycle  # noqa: E402

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



class UnknownActionError(Exception):
    """A POST named no q:action, or one that does not exist on the page."""



class _LocalDateTag(JSONTag):
    """A naive datetime in the session, kept naive (see QuantumWebServer.__init__, SET-5)."""
    __slots__ = ()
    key = ' qdt'

    def check(self, value) -> bool:
        return isinstance(value, datetime) and value.tzinfo is None

    def to_json(self, value):
        return value.isoformat()

    def to_python(self, value):
        return datetime.fromisoformat(value)

class QuantumWebServer(ConfigLoading, HtmlPostProcessing, ErrorPages, ServerLifecycle):
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
        self.app.secret_key = (
            os.environ.get('QUANTUM_SECRET_KEY')
            or self.config.get('security', {}).get('secret_key')
            # DEV-2: while developing, a key that survives the reloader — which
            # is a new process — so saving a file does not log everyone out.
            or (self._dev_secret_key(config_path) if self.config['server'].get('debug') else None)
            or secrets.token_hex(32)
        )
        # AUTH-5: the session cookie carries the login. HttpOnly keeps it from
        # page scripts; SameSite=Lax keeps another site from submitting a form
        # (a q:action) with it. Left to the browser's default before.
        self.app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
        # SET-5: a q:set of one expression keeps its type, so a session can
        # hold a date ({dateAdd('h', 8)}). Flask writes a date without a
        # timezone as UTC and reads it back as UTC — a local time shifted by the
        # server's offset: a session expiring in 1 hour was already expired in
        # UTC-3. A date without a timezone comes back the same date.
        # Its own session interface and serializer: Flask's are objects shared
        # by every app in the process.
        self.app.session_interface = SecureCookieSessionInterface()
        self.app.session_interface.serializer = TaggedJSONSerializer()
        self.app.session_interface.serializer.register(_LocalDateTag, index=0)
        # CFG-2: security.max_content_length (16 MB by default) was read into
        # the config and never handed to Flask, so a request body — an upload
        # — had no size limit at all.
        self.app.config['MAX_CONTENT_LENGTH'] = (
            (self.config.get('security') or {}).get('max_content_length') or 16 * 1024 * 1024)

        self.parser = QuantumParser()
        self.template_cache: Dict[str, Any] = {}  # AST cache
        # Flash helpers only (read/set the flash in the session). q:action
        # bodies run in a runtime built for each request (ACT-10), never in a
        # shared one.
        self.action_handler = ActionHandler(ComponentRuntime(config=self.config))

        # Phase F: Application scope (global state shared across all users)
        self.application_scope: Dict[str, Any] = {}

        # M12 (DEV-1): the /_dev panel records the last requests — only while
        # developing. With debug off nothing is recorded and /_dev is a 404.
        from quantum.runtime.dev_panel import DevPanel
        self.dev_panel = DevPanel() if self.config['server'].get('debug') else None

        # Setup routes
        self._setup_routes()
        self._setup_request_hooks()

        # Build dynamic route table for [param] segments
        self._dynamic_routes: List[DynamicRoute] = []
        self._build_dynamic_routes()


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

        if self.dev_panel is not None:
            @self.app.route('/_dev')
            @self.app.route('/_dev/<int:number>')
            def dev_panel(number=None):
                """M12: what the last requests did (debug only, this machine only).

                It shows sessions and query parameters. `debug` is dropped for
                the Werkzeug console off loopback, but the config flag — and a
                gunicorn bind — can still be public, so the panel checks who
                asks: from any other address it does not exist."""
                if request.remote_addr not in ('127.0.0.1', '::1'):
                    abort(404)
                return Response(self.dev_panel.render(number), mimetype='text/html')

        @self.app.route('/_stream/<token>')
        def llm_stream_route(token):
            """IA-7: a streamed answer, read once, by the session that asked for it."""
            from flask import stream_with_context
            from quantum.runtime import llm_stream
            job = llm_stream.take(token, session.get('quantum_session'))
            if job is None:
                abort(404)
            service = ComponentRuntime(config=self.config).services.multi_llm
            return Response(stream_with_context(llm_stream.run(job, service)),
                            mimetype='text/plain; charset=utf-8',
                            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

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
                message="The component you're looking for doesn't exist.",
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
            if self.dev_panel is not None and not request.path.startswith(('/_dev', '/static/', '/favicon')):
                request._quantum_dev = self.dev_panel.start(request.method, request.full_path.rstrip('?'))

        @self.app.after_request
        def after_request_hook(response):
            token = getattr(request, '_quantum_dev', None)
            if token is not None:
                self.dev_panel.finish(token, response.status_code, response.headers.get('Location'),
                                      session.get('flash'))
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
            if q_file.name.endswith('.test.q'):
                continue                                   # a test suite, not a page (ROUTE-4)
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

        # ROUTE-3: a file or folder whose name starts with `_` exists to be
        # imported, not visited. A layout like admin/AdminShell.q was served
        # at /admin/AdminShell and answered 500 (its required props missing).
        if any(part.startswith('_') for part in component_path.replace('\\', '/').split('/')):
            abort(404)

        # ROUTE-4: a *.test.q file is a test suite (TEST-1), never a page.
        if component_path.endswith('.test'):
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

        dev_note(component=str(file_path))
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
                    return redirect(getattr(ast, 'login_url', None) or self._login_url())

                # Check session expiry
                if AuthService.is_session_expired(session_data):
                    # Session expired - logout and redirect to login
                    AuthService.logout(session_data)
                    session.modified = True
                    return redirect((getattr(ast, 'login_url', None) or self._login_url()) + '?expired=true')

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

            # UI-13: a cell of an editable <ui:table> posts to the generated action.
            if request.method == 'POST' and request.form.get('action') == '__edit':
                return self._edit_cell(ast, path_params)

            # Check if this is an action request (POST/PUT/DELETE)
            if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                # Look for q:action in component
                try:
                    action_node = self._find_action_in_component(ast)
                except UnknownActionError as e:
                    return Response(f"<h1>400 Bad Request</h1><p>{html_escape(str(e))}</p>",
                                    status=400, mimetype='text/html')

                if action_node:
                    dev_note(action=action_node.name)
                    # AUTH-6: the page's guards run before its action. Without
                    # this a guard protected the GET only, and the POST ran
                    # the action with no session.
                    guard_runtime = ComponentRuntime(config=self.config)
                    try:
                        guard_runtime.run_guards(ast, self._page_params(path_params, consume_flash=False))
                    except PageRedirect as r:
                        return self._page_redirect(r, guard_runtime)
                    session['quantum_session'] = guard_runtime.execution_context.session_vars

                    # Handle action — in THIS request's runtime (ACT-10). It
                    # used to run in one ComponentRuntime shared by every
                    # request and thread, which never registered the page's
                    # q:functions: calling one inside an action was a 500.
                    # guard_runtime has entered this component with this
                    # request's scopes.
                    try:
                        redirect_url, status_code = ActionHandler(guard_runtime).handle_action(
                            action_node, route_params=path_params)
                    except PageRedirect as r:
                        # q:redirect reached through a q:function or q:loop in the action
                        return self._page_redirect(r)

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

            params = self._page_params(path_params)

            # Execute component (runs queries, loops, functions, etc.)
            runtime = ComponentRuntime(config=self.config)
            try:
                runtime.execute_component(ast, params)
            except PageRedirect as r:
                # ACT-7: q:redirect outside an action ends the page.
                return self._page_redirect(r, runtime)
            finally:
                dev_scopes(runtime.execution_context)

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
            renderer = HTMLRenderer(runtime.execution_context,
                                    components_dir=self.config['paths']['components'],
                                    function_resolver=runtime._resolve_expression_function,
                                    config=self.config)
            # UI-9: after a failed validation, the form shows the values sent
            # and each error by its field — once, like the flash.
            renderer.form_state = session.pop('form_state', None)
            renderer._ui_action_nodes = {s.name: s for s in ast.statements if isinstance(s, ActionNode)}
            from quantum.runtime.ui_table_edit import query_nodes
            renderer._query_nodes = query_nodes(ast)

            # UI-3: a renderer that is not a browser (the console) asks for the
            # page as a tree of view nodes instead of HTML. Same page, same
            # runtime, same actions — only the drawing differs.
            if 'application/vnd.quantum.view+json' in (request.headers.get('Accept') or ''):
                from quantum.runtime.ui_view import UIViewBuilder, page_title
                import json as _json
                payload = {
                    'title': page_title(ast, renderer),
                    'flash': params.get('flash', ''), 'flashType': params.get('flashType', ''),
                    'view': UIViewBuilder(renderer).build(
                        [s for s in ast.statements if not isinstance(s, ActionNode)]),
                }
                return Response(_json.dumps(payload, ensure_ascii=False, default=str),
                                mimetype='application/vnd.quantum.view+json')

            try:
                html = renderer.render(ast)
            except PageRedirect as r:
                # A component called from the markup redirected.
                return self._page_redirect(r, runtime)
            # UI-12: a search field refreshes an element by id; one that is not
            # on the page would make every keystroke swap nothing, silently.
            for target in sorted(getattr(renderer, '_search_targets', ()) or ()):
                if not re.search(r'(?<![\w-])id="' + re.escape(target) + '"', html):
                    raise ValueError(f'<ui:input search="{target}">: there is no element with id="{target}" '
                                     f'on this page to refresh (UI-12)')

            # Phase B: For partial requests, return only component HTML
            if partial:
                return Response(html, mimetype='text/html')

            # For full page requests, add HTMX support
            if '<html' in html.lower():
                # Component already has full HTML structure - inject HTMX into it
                full_html = self._inject_htmx(html)
            else:
                # Fragment component - wrap with full page + HTMX
                from quantum.runtime.ui_view import page_title
                full_html = self._wrap_with_htmx(html, component_path, page_title(ast, renderer))

            # Extract inline CSS and JS to external files
            full_html = self._extract_inline_assets(full_html)

            # Pretty-print HTML for readable View Source
            full_html = self._prettify_html(full_html)

            return Response(full_html, mimetype='text/html')

        except QuantumParseError as e:
            dev_note(error=str(e), where=self._error_location(e, file_path))
            # Enhanced parse error with context
            ErrorHandler.handle_parse_error(e, component_path)

            if self.config['server']['debug']:
                # Show enhanced error in debug mode
                # The message says what to change; the generic XML hints of
                # ErrorHandler were wrong for most parse errors (a statement in
                # markup is not an XML syntax problem).
                return self._render_error_page(
                    title="Parse Error",
                    message=f"Could not parse component: {component_path}",
                    details=str(e),
                    suggestion="",
                    location=self._error_location(e, file_path),
                ), 400
            else:
                return self._render_error_page(
                    title="Parse Error",
                    message="Could not parse component",
                    details="Enable debug mode for details",
                    suggestion=""
                ), 400

        except QuantumError as e:
            dev_note(error=str(e), where=self._error_location(e, file_path))
            logging.getLogger('quantum.server').error("page %s failed: %s", component_path, e)
            # Already enhanced error
            return self._render_error_page(
                title="Quantum Error",
                message=e.message,
                details=str(e),
                suggestion=e.suggestion or "Check the error details above",
                location=self._error_location(e, file_path) if self.config['server']['debug'] else None,
            ), 500

        except HTTPException:
            # 413 (CFG-2), 400 for a malformed form: Flask answers these with
            # their own status. Caught below they became a 500.
            raise

        except Exception as e:
            dev_note(error=f'{type(e).__name__}: {e}', where=self._error_location(e, file_path))
            # The page says little in production; the log must say everything.
            # This branch used to leave no trace at all: a 500 with nothing to read.
            logging.getLogger('quantum.server').exception(
                "page %s failed: %s", component_path, e)
            if self.config['server']['debug']:
                # Enhanced runtime error
                ErrorHandler.handle_runtime_error(e, str(component_path), component_path)

                import traceback
                return self._render_error_page(
                    title="Runtime Error",
                    message=f"Error in component: {component_path}",
                    details=str(e),
                    suggestion="",
                    location=self._error_location(e, file_path),
                    python_traceback=traceback.format_exc(),
                ), 500
            else:
                # Generic error in production
                return self._render_error_page(
                    title="Error",
                    message="An error occurred",
                    details="Enable debug mode for more details.",
                    suggestion=""
                ), 500

    # Attributes and API calls that mean a page actually needs htmx. Kept
    # deliberately broad — injecting an unused script is wasteful, but failing
    # to inject a needed one breaks the page, so ambiguity favours injecting.
    _HTMX_MARKERS = ('hx-', 'data-hx-', 'htmx.')

    def _edit_cell(self, ast, path_params) -> Response:
        """UI-13: the generated action of an editable <ui:table>.

        It edits only a table and column the page declares editable, runs the
        page's guards first (AUTH-6), validates the value with the column's
        rules from the schema (UI-10) and updates one row by its key through
        the database service — so /_dev shows it like any action."""
        from quantum.runtime.table_params import TableParamsError, columns_of, param_from_column
        from quantum.runtime.ui_table_edit import EDIT_ACTION, find_editable_table
        from quantum.runtime.action_handler import ValidationError

        table = request.form.get('__table', '')
        column = request.form.get('__column', '')
        key = request.form.get('__key', '')
        value = request.form.get('value')
        dev_note(action=f'{EDIT_ACTION} {table}.{column}')
        target = find_editable_table(ast, table, column)
        if target is None:
            return Response(f'<h1>400 Bad Request</h1><p>{html_escape(table)}.{html_escape(column)} '
                            f'is not editable on this page.</p>', status=400, mimetype='text/html')

        guard_runtime = ComponentRuntime(config=self.config)
        try:
            guard_runtime.run_guards(ast, self._page_params(path_params, consume_flash=False))
        except PageRedirect as r:
            return self._page_redirect(r, guard_runtime)

        back = request.referrer or request.path
        try:
            columns_by_name = {c.name: c for c in columns_of(self.config, target.edit_datasource, table)}
        except TableParamsError as exc:
            raise ValueError(f'<ui:table edit="{table}">: {exc} (UI-13)') from exc
        keys = [c for c in columns_by_name.values() if c.primary_key]
        if column not in columns_by_name or columns_by_name[column].primary_key or len(keys) != 1:
            return Response('<h1>400 Bad Request</h1>', status=400, mimetype='text/html')
        param = param_from_column(columns_by_name[column])
        param.name = 'value'

        class _Action:                     # what the validation reads of an action: where FKs are
            table_datasource = target.edit_datasource
        try:
            validated = ActionHandler(guard_runtime)._validate_parameters(
                [param], {'value': value} if value is not None else {}, _Action)
        except ValidationError as error:
            self.action_handler._set_flash_message(str(error), 'error')
            session['form_state'] = {'action': EDIT_ACTION, 'cell': f'{column}@{key}',
                                     'errors': {'value': error.fields.get('value', str(error))},
                                     'values': {'value': value or ''}}
            session.modified = True
            return redirect(back)
        new_value = validated.get('value')
        if str(param.type) == 'boolean':
            new_value = 1 if str(new_value).lower() in ('true', '1', 'on', 'yes') else 0
        key_value = int(key) if 'INT' in (keys[0].type or '').upper() and key.lstrip('-').isdigit() else key
        from quantum.runtime import history
        token = history.enter(f'{EDIT_ACTION} {table}.{column}',
                              guard_runtime.execution_context.session_vars)      # M22
        try:
            result = guard_runtime.services.database.execute_query(
                target.edit_datasource,
                f'UPDATE "{table}" SET "{column}" = :value WHERE "{keys[0].name}" = :key',
                {'value': new_value, 'key': key_value})
        finally:
            history.leave(token)
        if not result.affected_rows:
            self.action_handler._set_flash_message(f'No row of {table} with {keys[0].name} = {key}', 'error')
        else:
            self.action_handler._set_flash_message(f'Saved: {column}', 'success')
        return redirect(back)

    def _page_params(self, path_params, consume_flash: bool = True) -> Dict[str, Any]:
        """The variables and scopes a page runs with (render, and guards before an action)."""
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
        # ACT-3: always defined — '' when there is no message — so a page can
        # pass {flash} to a layout component without failing when there is
        # none (a missing name in a prop is an error, COMP-2).
        # Guards before an action read it without taking it from the next page.
        flash_data = (self.action_handler.get_flash_message() if consume_flash
                      else session.get('flash'))
        params['flash'] = flash_data['message'] if flash_data else ''
        params['flashType'] = flash_data['type'] if flash_data else ''

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
        return params

    def _page_redirect(self, r, runtime=None):
        """Turn a q:redirect outside an action (PageRedirect) into the response."""
        from quantum.runtime.executors.services.file_executor import PageFile
        if isinstance(r, PageFile):                                  # FILE-2
            if r.path is None:
                abort(404)
            from flask import send_file
            if runtime is not None:
                session['quantum_session'] = runtime.execution_context.session_vars
            return send_file(r.path, as_attachment=True, download_name=r.name,
                             mimetype=r.mimetype or 'application/octet-stream')
        if runtime is not None:
            # A logout page clears the session and redirects: keep what it set.
            session['quantum_session'] = runtime.execution_context.session_vars
        if r.flash:
            self.action_handler._set_flash_message(r.flash, r.flash_type)
        session.modified = True
        return redirect(r.url, code=r.status)

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

        # Multiple actions: match by 'action' form field (ACT-1)
        requested_action = request.form.get('action', '')
        for node in action_nodes:
            if requested_action and getattr(node, 'name', '') == requested_action:
                return node

        # ACT-5: no silent fallback. This used to run the FIRST action when the
        # name was missing or matched nothing — a POST meant for "excluir" with
        # a typo ran "criar".
        available = ', '.join(getattr(n, 'name', '?') for n in action_nodes)
        if requested_action:
            raise UnknownActionError(
                f"No q:action named '{requested_action}' on this page. Available: {available}.")
        raise UnknownActionError(
            f"This page has several q:action ({available}); the form must say which one "
            f"with a field named 'action'.")


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

    def _login_url(self) -> str:
        """AUTH-4: where require_auth sends a visitor (security.login_url, default /login)."""
        # Validated at startup by _validate_config (a local path only).
        return ((self.config.get('security') or {}).get('login_url') or '/login').strip()

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
