"""
Endpoint Parser - Parse q:endpoint and q:respond (API-1, API-2): a component's REST API
"""

import re
from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import EndpointNode, RespondNode

_UNITS = {'second': 1, 'minute': 60, 'hour': 3600, 'day': 86400}
_SIZES = {'b': 1, 'kb': 1024, 'mb': 1024 ** 2, 'gb': 1024 ** 3}


def _error(message: str):
    from quantum.core.parser import QuantumParseError
    return QuantumParseError(message)


class EndpointParser(BaseTagParser):
    """
    Parser for q:endpoint.

    Examples:
        <q:endpoint method="GET">
            <q:query name="rows" datasource="db">SELECT id, title FROM cards</q:query>
            <q:respond json="{rows}" />
        </q:endpoint>
        <q:endpoint method="POST" require_role="member" origins="https://example.com"
                    limit="10/minute" maxsize="64kb">
            <q:param name="title" type="string" required="true" maxlength="120" />
            ...
            <q:respond status="201" json="{ {'id': added[0].id} }" />
        </q:endpoint>
    """

    @property
    def tag_names(self) -> List[str]:
        return ['endpoint']

    def parse(self, element: ET.Element) -> EndpointNode:
        method = (element.get('method') or '').strip().upper()
        if method not in EndpointNode.METHODS:
            raise _error(f'<q:endpoint method="{element.get("method", "")}">: the method is one of '
                         f'{", ".join(EndpointNode.METHODS)} (API-1)')
        node = EndpointNode(method)
        where = f'<q:endpoint method="{method}">'

        role = element.get('require_role')
        if role is not None:
            roles = [r.strip() for r in role.split(',') if r.strip()]
            if not roles:
                raise _error(f'{where} require_role= names no role')
            node.require_role = ','.join(roles)

        origins = element.get('origins')
        if origins is not None:
            for origin in (o.strip() for o in origins.split(',') if o.strip()):
                if origin != '*' and not re.fullmatch(r'https?://[^/\s]+', origin):
                    raise _error(f'{where} origins="{origins}": each origin is a scheme and a host '
                                 f'(https://example.com, no path), or * for any (API-4)')
                node.origins.append(origin.rstrip('/'))

        limit = element.get('limit')
        if limit is not None:
            match = re.fullmatch(r'\s*(\d+)\s*/\s*(second|minute|hour|day)\s*', limit)
            if not match or int(match.group(1)) < 1:
                raise _error(f'{where} limit="{limit}": so many calls per second, minute, hour or day '
                             f'from one address, as "10/minute" (API-5)')
            node.limit = (int(match.group(1)), _UNITS[match.group(2)])

        size = element.get('maxsize')
        if size is not None:
            match = re.fullmatch(r'\s*(\d+)\s*(b|kb|mb|gb)\s*', size.lower())
            if not match:
                raise _error(f'{where} maxsize="{size}": a size, as "64kb" or "2mb" (API-5)')
            node.max_size = int(match.group(1)) * _SIZES[match.group(2)]

        for child in element:
            if self._get_element_name(child) == 'param':
                node.add_param(self.parse_param(child))
            else:
                statement = self.parse_child(child)
                if statement:
                    node.add_statement(statement)
        return node


class RespondParser(BaseTagParser):
    """q:respond json="{expression}" status="201": what a q:endpoint answers (API-2)."""

    @property
    def tag_names(self) -> List[str]:
        return ['respond']

    def parse(self, element: ET.Element) -> RespondNode:
        status = element.get('status', '200')
        if not re.fullmatch(r'\d{3}', status.strip()) or not 100 <= int(status) <= 599:
            raise _error(f'<q:respond status="{status}">: an HTTP status, 100 to 599 (API-2)')
        json_expr = element.get('json')
        if json_expr is not None and not json_expr.strip():
            json_expr = None
        return RespondNode(json_expr, int(status))
