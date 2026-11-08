"""
The application's API described for whoever calls it: /api/openapi.json (SPEC.md, API-7).

Every component with q:endpoint is a path of the document, at its route (a `[name]` segment as `{name}`); each
endpoint is an operation with what a caller needs to rely on: its parameters, their types and rules (the query
string for GET and DELETE, a JSON body otherwise), the statuses its q:responds answer, the refusals it may
give (API-1 to API-5) and who may call it (API-3). It is read from the components as they are, so it is never
out of date; `quantum check --openapi FILE` writes the same document without a server.
"""

import ast
import re
from http import HTTPStatus
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from quantum.core.ast_nodes import EndpointNode, RespondNode
from quantum.runtime.param_validation import FILE_TYPES, FLOAT_TYPES, INT_TYPES

OPENAPI_VERSION = '3.1.0'
PATH = '/api/openapi.json'

_WITH_QUERY = ('GET', 'DELETE')       # API-1: their q:params come from the query string
_ERRORS = {
    400: 'The body is not a JSON object.',
    401: 'No one is signed in.',
    403: 'The one signed in may not, a guard of the component refused, or the page is of another site (origins=).',
    413: 'The body is larger than maxsize=.',
    415: 'The body is not JSON (nor a form).',
    422: 'A parameter did not pass: each field that failed, by its name.',
    429: 'Too many calls from this address (limit=); Retry-After says when to try again.',
    500: 'The endpoint failed; the server\'s log says why.',
}


def routes(components: Path) -> Iterator[Tuple[str, Path, List[str]]]:
    """(the URL path in OpenAPI's form, the file, its route segments) of each component that could be
    served (ROUTE-1, ROUTE-3, ROUTE-4), in the order of their paths."""
    found = []
    for file in components.rglob('*.q'):
        rel = file.relative_to(components).as_posix()[:-2]
        parts = rel.split('/')
        if file.name.endswith('.test.q') or any(p.startswith('_') for p in parts):
            continue
        if parts[-1] == 'index':
            parts = parts[:-1]
        segments, shown = [], []
        for part in parts:
            m = re.fullmatch(r'\[(?:\.\.\.)?(\w+)\]', part)
            if m:
                segments.append(m.group(1))
                shown.append('{' + m.group(1) + '}')
            else:
                shown.append(part)
        found.append(('/' + '/'.join(shown), file, segments))
    return iter(sorted(found, key=lambda r: r[0]))


def _statements(nodes) -> Iterator[Any]:
    """Every statement inside, in q:if's branches and loops too."""
    for node in nodes or []:
        yield node
        for field in ('statements', 'body', 'if_body', 'else_body', 'children'):
            inner = getattr(node, field, None)
            if isinstance(inner, list):
                yield from _statements(inner)
        for block in getattr(node, 'elseif_blocks', None) or []:
            body = block.get('body') if isinstance(block, dict) else getattr(block, 'body', None)
            yield from _statements(body)


def _ends_with_respond(nodes) -> bool:
    """API-2: an endpoint whose last statement is a q:respond always answers it; any other may answer 204."""
    return bool(nodes) and isinstance(nodes[-1], RespondNode)


def _reason(status: int) -> str:
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return f'Status {status}'


def _shape(json_expr: str) -> Dict[str, Any]:
    """What a q:respond's json= answers, as far as it can be read: a dictionary written in the attribute
    (EXPR-17) is an object with its keys; anything else is any JSON."""
    text = json_expr.strip()
    if text.startswith('{') and text.endswith('}'):
        text = text[1:-1].strip()
    try:
        tree = ast.parse(text, mode='eval').body
    except SyntaxError:
        return {}
    if isinstance(tree, ast.Dict) and tree.keys and all(
            isinstance(k, ast.Constant) and isinstance(k.value, str) for k in tree.keys):
        return {'type': 'object', 'properties': {k.value: {} for k in tree.keys},
                'required': [k.value for k in tree.keys]}
    if isinstance(tree, ast.List):
        return {'type': 'array'}
    return {}


def _number(text) -> Optional[float]:
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return int(value) if value.is_integer() else value


def schema_of(param) -> Dict[str, Any]:
    """A q:param as JSON Schema: its type and the rules ACT-2 checks."""
    ptype = (param.type or 'string').lower()
    if ptype in INT_TYPES:
        schema: Dict[str, Any] = {'type': 'integer'}
    elif ptype in FLOAT_TYPES:
        schema = {'type': 'number'}
    elif ptype == 'boolean':
        schema = {'type': 'boolean'}
    elif ptype == 'email':
        schema = {'type': 'string', 'format': 'email'}
    elif ptype == 'url':
        schema = {'type': 'string', 'format': 'uri'}
    elif ptype == 'date':
        schema = {'type': 'string', 'format': 'date'}
    elif ptype in FILE_TYPES:
        schema = {'type': 'string', 'format': 'binary'}
    elif ptype == 'array':
        schema = {'type': 'array'}
    elif ptype == 'object':
        schema = {'type': 'object'}
    elif ptype in ('any', 'json'):
        schema = {}
    else:
        schema = {'type': 'string'}
    for rule, key in (('min', 'minimum'), ('max', 'maximum')):
        value = _number(getattr(param, rule, None))
        if value is not None:
            schema[key] = value
    if getattr(param, 'range', None) and '..' in str(param.range):
        low, high = (_number(v) for v in str(param.range).split('..', 1))
        if low is not None:
            schema['minimum'] = low
        if high is not None:
            schema['maximum'] = high
    if param.minlength is not None:
        schema['minLength'] = param.minlength
    if param.maxlength is not None:
        schema['maxLength'] = param.maxlength
    if param.pattern:
        schema['pattern'] = param.pattern
    if param.enum:
        schema['enum'] = [v.strip() for v in str(param.enum).split(',') if v.strip()]
    if param.default not in (None, ''):
        from quantum.runtime.param_validation import coerce
        value, error = coerce(param, param.default)
        if not error:
            schema['default'] = value
    if param.description:
        schema['description'] = param.description
    return schema


def _roles(component, endpoint: EndpointNode) -> Optional[List[str]]:
    """API-3: who may call it: None when anyone may, [] when whoever is signed in, else the roles."""
    roles: Optional[List[str]] = None
    if getattr(component, 'require_auth', False):
        roles = [r.strip() for r in (component.require_role or '').split(',') if r.strip()]
    if endpoint.require_role:
        roles = [r.strip() for r in endpoint.require_role.split(',') if r.strip()]
    return roles


def operation(component, endpoint: EndpointNode, route: str, segments: List[str]) -> Dict[str, Any]:
    """One endpoint as an OpenAPI operation."""
    op: Dict[str, Any] = {
        'operationId': endpoint.method.lower() + ''.join(
            w.capitalize() for w in re.findall(r'[A-Za-z0-9]+', route)) or endpoint.method.lower(),
    }
    if getattr(endpoint, 'description', None):
        op['summary'] = endpoint.description
    parameters: List[Dict[str, Any]] = [
        {'name': name, 'in': 'path', 'required': True, 'schema': {'type': 'string'}} for name in segments]
    params = [p for p in endpoint.params if p.name not in segments]      # ROUTE-2: the route's wins
    if endpoint.method in _WITH_QUERY:
        for p in params:
            parameters.append({'name': p.name, 'in': 'query', 'required': bool(p.required),
                               'schema': schema_of(p)})
    elif params:
        body = {'type': 'object', 'properties': {p.name: schema_of(p) for p in params}}
        required = [p.name for p in params if p.required]
        if required:
            body['required'] = required
        if any((p.type or '').lower() in FILE_TYPES for p in params):
            content = {'multipart/form-data': {'schema': body}}
        else:
            content = {'application/json': {'schema': body},
                       'application/x-www-form-urlencoded': {'schema': body}}
        op['requestBody'] = {'required': bool(required), 'content': content}
    if parameters:
        op['parameters'] = parameters

    responses: Dict[str, Any] = {}
    for node in _statements(endpoint.body):
        if isinstance(node, RespondNode) and str(node.status) not in responses:
            answer: Dict[str, Any] = {'description': _reason(node.status)}
            if node.json_expr is not None:
                answer['content'] = {'application/json': {'schema': _shape(node.json_expr)}}
            responses[str(node.status)] = answer
    if not _ends_with_respond(endpoint.body) and '204' not in responses:
        responses['204'] = {'description': _reason(204)}

    errors = []
    if endpoint.method not in _WITH_QUERY and params:
        errors += [400, 415]
    roles = _roles(component, endpoint)
    if roles is not None:
        errors.append(401)
    from quantum.core.guards import page_guards
    if roles or endpoint.origins or page_guards(component):
        errors.append(403)
    if endpoint.max_size is not None:
        errors.append(413)
    if params:
        errors.append(422)
    if endpoint.limit is not None:
        errors.append(429)
    errors.append(500)
    for status in sorted(set(errors)):
        answer = {'description': _ERRORS[status],
                  'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Error'}}}}
        if status == 429:
            answer['headers'] = {'Retry-After': {'schema': {'type': 'integer'},
                                                 'description': 'Seconds until a call may be made again.'}}
        responses[str(status)] = answer
    op['responses'] = dict(sorted(responses.items()))

    if roles is not None:
        op['security'] = [{'session': roles}]        # OpenAPI 3.1: role names for a scheme that is not OAuth
    if endpoint.origins:
        op['x-origins'] = list(endpoint.origins)
    if endpoint.limit is not None:
        count, seconds = endpoint.limit
        unit = {1: 'second', 60: 'minute', 3600: 'hour', 86400: 'day'}[seconds]
        op['x-limit'] = f'{count}/{unit}'
    if endpoint.max_size is not None:
        op['x-maxsize'] = endpoint.max_size
    return op


def endpoints(components: Path, parse) -> Iterator[Tuple[str, Path, Any, List[EndpointNode], List[str]]]:
    """(route, file, component, its endpoints, its route segments) of each component with q:endpoint.
    `parse` reads a file into its component; a file that does not parse is left out (quantum check says so)."""
    for route, file, segments in routes(components):
        try:
            text = file.read_text(encoding='utf-8')
        except OSError:
            continue
        if 'endpoint' not in text:
            continue
        try:
            component = parse(file)
        except Exception:
            continue
        found = [s for s in getattr(component, 'statements', None) or [] if isinstance(s, EndpointNode)]
        if found:
            yield route, file, component, found, segments


def document(components: Path, parse, title: str, version: str = '1',
             cookie: str = 'session') -> Optional[Dict[str, Any]]:
    """API-7: the OpenAPI document of the application's endpoints; None when it has none."""
    paths: Dict[str, Any] = {}
    protected = False
    for route, _file, component, found, segments in endpoints(components, parse):
        item = paths.setdefault(route, {})
        for endpoint in sorted(found, key=lambda e: EndpointNode.METHODS.index(e.method)):
            op = operation(component, endpoint, route, segments)
            protected = protected or 'security' in op
            item[endpoint.method.lower()] = op
    if not paths:
        return None
    doc: Dict[str, Any] = {
        'openapi': OPENAPI_VERSION,
        'info': {'title': title, 'version': version,
                 'description': 'Generated by Quantum from the application\'s q:endpoints (SPEC.md, API-7).'},
        'paths': paths,
        'components': {'schemas': {'Error': {
            'type': 'object', 'required': ['error', 'message'],
            'properties': {'error': {'type': 'string'}, 'message': {'type': 'string'},
                           'fields': {'type': 'object', 'additionalProperties': {'type': 'string'}},
                           'allowed': {'type': 'array', 'items': {'type': 'string'}},
                           'retry_after': {'type': 'integer'}, 'max_bytes': {'type': 'integer'}}}}},
    }
    if protected:
        doc['components']['securitySchemes'] = {'session': {
            'type': 'apiKey', 'in': 'cookie', 'name': cookie,
            'description': 'The session of whoever signed in; its roles are the ones an operation lists.'}}
    return doc
