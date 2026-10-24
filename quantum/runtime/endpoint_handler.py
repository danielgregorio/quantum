"""
A component's REST API: q:endpoint, answering JSON (SPEC.md, API-1 to API-6).

A component with q:endpoint is an API. Each method it has an endpoint for runs that endpoint: its q:params
come from the JSON body (the query string for GET and DELETE) and are validated as an action's (ACT-2), its
statements run as an action's do, and q:respond answers. Everything it answers is JSON: a refusal, a
failure, a method it has no endpoint for. Its guards and roles are a page's; a browser on another site may
call it only when origins= names that site, at most limit= times from one address, with a body no larger
than maxsize=.
"""

import json
import logging
import threading
import time
from collections import deque
from typing import Any, Dict, Optional

from flask import Response, request, session

from quantum.core.ast_nodes import EndpointNode, RespondNode
from quantum.runtime.action_handler import ActionHandler, ValidationError
from quantum.runtime.auth_service import AuthService
from quantum.runtime.component import ComponentRuntime
from quantum.runtime.execution_context import ExecutionContext

logger = logging.getLogger('quantum.endpoint')

_NO_BODY = object()


class _Reply:
    """What q:respond answered; it ends the endpoint's statements."""

    def __init__(self, status: int, payload: Any):
        self.status = status
        self.payload = payload


class EndpointHandler(ActionHandler):
    """An endpoint's statements run as an action's (the same executors, q:if, the history), with
    q:respond in place of q:redirect."""

    def _execute_one(self, statement, context):
        if isinstance(statement, RespondNode):
            if statement.json_expr is None:
                return _Reply(statement.status, _NO_BODY)
            value = self.component_runtime._apply_databinding(statement.json_expr, context.get_all_variables())
            return _Reply(statement.status, value)
        return super()._execute_one(statement, context)

    def run(self, endpoint: EndpointNode, data: Dict[str, Any], route_params: Dict[str, str]) -> Optional[_Reply]:
        context = ExecutionContext()
        context.session_vars = session.get('quantum_session', {})
        context.application_vars = self.component_runtime.execution_context.application_vars
        for key, value in self._validate_parameters(endpoint.params, data, None).items():
            context.set_variable(key, value)
        context.set_variable('body', data)              # API-1: what was sent, as sent
        for key, value in (route_params or {}).items():  # ROUTE-2: the path's segments, set last
            context.set_variable(key, value)
        from quantum.runtime import history
        token = history.enter(f'{endpoint.method} {request.path}', context.session_vars)
        try:
            reply = self._execute_statements(endpoint.body, context)
        finally:
            history.leave(token)
            from quantum.runtime.dev_panel import note_scopes
            note_scopes(context, 'endpoint')
        session['quantum_session'] = context.session_vars
        session.modified = True
        return reply if isinstance(reply, _Reply) else None


class RateLimiter:
    """API-5: so many calls in so many seconds from one address, per endpoint; in the server's memory."""

    def __init__(self):
        self._calls: Dict[tuple, deque] = {}
        self._lock = threading.Lock()

    def allow(self, key: tuple, count: int, seconds: int) -> int:
        """0 when the call may go on, else the seconds until it may."""
        now = time.monotonic()
        with self._lock:
            calls = self._calls.setdefault(key, deque())
            while calls and now - calls[0] >= seconds:
                calls.popleft()
            if len(calls) >= count:
                return max(1, int(seconds - (now - calls[0])) + 1)
            calls.append(now)
            if len(self._calls) > 10000:            # forget the addresses that have gone quiet
                for stale in [k for k, v in self._calls.items() if not v or now - v[-1] > 86400]:
                    del self._calls[stale]
            return 0



def _own_origin() -> str:
    return request.host_url.rstrip('/')


def _allowed(endpoint: EndpointNode, origin: Optional[str]) -> bool:
    """API-4: a request without an Origin (a game on the desktop, a script) or from this server's own pages
    goes on; from another site's page only when origins= names it."""
    if not origin or origin == _own_origin():
        return True
    return '*' in endpoint.origins or origin.rstrip('/') in endpoint.origins


def _json(status: int, payload: Any = _NO_BODY, headers: Optional[Dict[str, str]] = None) -> Response:
    if payload is _NO_BODY:
        response = Response(status=status)
    else:
        response = Response(json.dumps(payload, ensure_ascii=False, default=str), status=status,
                            mimetype='application/json')
    for name, value in (headers or {}).items():
        response.headers[name] = value
    return response


def _error(status: int, error: str, message: str, **more) -> Response:
    return _json(status, {'error': error, 'message': message, **more})


def _cors(response: Response, endpoint: Optional[EndpointNode], origin: Optional[str]) -> Response:
    """API-4: the answer a browser on an allowed site may read."""
    if origin and endpoint is not None and origin != _own_origin() and _allowed(endpoint, origin):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.vary.add('Origin')
    return response


def _data(endpoint: EndpointNode):
    """API-1: the q:params' values, from the JSON body (or a form's), or the query string for GET and
    DELETE without a body; or the refusal."""
    if endpoint.method in ('GET', 'DELETE') and not request.get_data(cache=True):
        return request.args.to_dict(), None
    raw = request.get_data(cache=True)
    if not raw:
        return {}, None
    if request.is_json:
        data = request.get_json(silent=True)
        if data is None:
            return None, _error(400, 'json', 'The body is not JSON.')
        if not isinstance(data, dict):
            return None, _error(400, 'json', 'The body is a JSON object: its keys are the parameters.')
        return data, None
    if request.mimetype in ('application/x-www-form-urlencoded', 'multipart/form-data'):
        return request.form.to_dict(), None
    return None, _error(415, 'content_type', 'Send the body as application/json.')


def serve_endpoint(server, ast, route_params: Dict[str, str]) -> Response:
    """API-1 to API-6: a request to a component with q:endpoint."""
    endpoints = {s.method: s for s in ast.statements if isinstance(s, EndpointNode)}
    allowed_methods = ', '.join(sorted(endpoints) + (['HEAD'] if 'GET' in endpoints else []) + ['OPTIONS'])
    origin = request.headers.get('Origin')
    method = 'GET' if request.method == 'HEAD' else request.method

    if method == 'OPTIONS':
        # API-4: a browser asks first whether its page may call; only an allowed site is told yes
        asked = endpoints.get(request.headers.get('Access-Control-Request-Method', '').upper())
        response = _json(204, headers={'Allow': allowed_methods})
        if asked is not None and origin and _allowed(asked, origin):
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = ', '.join(
                m for m, e in sorted(endpoints.items()) if _allowed(e, origin))
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            response.headers['Access-Control-Max-Age'] = '600'
            response.vary.add('Origin')
        return response

    endpoint = endpoints.get(method)
    if endpoint is None:
        response = _error(405, 'method', f'{request.method} is not an endpoint of {request.path}.',
                          allowed=sorted(endpoints))
        response.headers['Allow'] = allowed_methods
        return response
    from quantum.runtime.dev_panel import note as dev_note
    dev_note(action=f'endpoint {endpoint.method}')

    if not _allowed(endpoint, origin):
        return _error(403, 'origin', f'A page of {origin} may not call this endpoint (origins=).')

    # API-5: a body too large, or too many calls, are refused before anything runs
    if endpoint.max_size is not None and (request.content_length or 0) > endpoint.max_size:
        return _cors(_error(413, 'too_large', f'The body is larger than {endpoint.max_size} bytes.',
                            max_bytes=endpoint.max_size), endpoint, origin)
    if endpoint.limit is not None:
        count, seconds = endpoint.limit
        limiter = server.__dict__.setdefault('_endpoint_limiter', RateLimiter())   # each server its counts
        wait = limiter.allow((request.path, endpoint.method, request.remote_addr), count, seconds)
        if wait:
            response = _error(429, 'rate_limited', f'At most {count} calls in {seconds} seconds; '
                                                   f'try again in {wait}.', retry_after=wait)
            response.headers['Retry-After'] = str(wait)
            return _cors(response, endpoint, origin)

    # API-3: the component's and the endpoint's roles, answered in JSON (401: who are you; 403: not you)
    if 'quantum_session' not in session:
        session['quantum_session'] = {}
    session_data = session['quantum_session']
    needs_login = getattr(ast, 'require_auth', False) or endpoint.require_role
    if needs_login and (not AuthService.is_authenticated(session_data)
                        or AuthService.is_session_expired(session_data)):
        return _cors(_error(401, 'unauthenticated', 'Sign in first.'), endpoint, origin)
    if getattr(ast, 'require_auth', False):
        if ast.require_role and not AuthService.has_role(session_data, ast.require_role):
            return _cors(_error(403, 'forbidden', f'Only {ast.require_role}.'), endpoint, origin)
        if ast.require_permission and not AuthService.has_permission(session_data, ast.require_permission):
            return _cors(_error(403, 'forbidden', f'Only with {ast.require_permission}.'), endpoint, origin)
    if endpoint.require_role and not AuthService.has_role(session_data, endpoint.require_role):
        return _cors(_error(403, 'forbidden', f'Only {endpoint.require_role}.'), endpoint, origin)

    from quantum.runtime.executors.control_flow.redirect_executor import PageRedirect
    runtime = ComponentRuntime(config=server.config)
    try:
        runtime.run_guards(ast, server._page_params(route_params, consume_flash=False))
    except PageRedirect:
        return _cors(_error(403, 'forbidden', 'A guard of the component refused it.'), endpoint, origin)

    data, refusal = _data(endpoint)
    if refusal is not None:
        return _cors(refusal, endpoint, origin)

    try:
        reply = EndpointHandler(runtime).run(endpoint, data, route_params)
    except ValidationError as e:
        # API-1: every field that failed, by its name
        return _cors(_error(422, 'invalid', str(e), fields=e.fields), endpoint, origin)
    except PageRedirect:
        logger.error('q:endpoint %s %s: a q:redirect ran (through a q:function?)', endpoint.method, request.path)
        return _cors(_error(500, 'server', 'The endpoint tried to redirect; an endpoint answers JSON.'),
                     endpoint, origin)
    except Exception as e:                             # API-6: a failure is a JSON error, and logged
        logger.exception('q:endpoint %s %s failed: %s', endpoint.method, request.path, e)
        from quantum.core.xml_lines import error_location
        file, line = error_location(e)
        dev_note(error=f'q:endpoint {endpoint.method} {request.path}: {e}', where=(file, line) if line else None)
        debug = bool((server.config.get('server') or {}).get('debug'))
        return _cors(_error(500, 'server', str(e) if debug else 'The endpoint failed; the server\'s log says why.'),
                     endpoint, origin)

    if reply is None:
        return _cors(_json(204), endpoint, origin)
    return _cors(_json(reply.status, reply.payload), endpoint, origin)
