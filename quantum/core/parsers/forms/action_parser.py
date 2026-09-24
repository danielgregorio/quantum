"""
Action Parser - Parse q:action statements for form handling
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import ActionNode


_NEVER_ENFORCED = {
    'require_auth': 'Protect the page with require_auth / require_role on the '
                    'q:component: that covers its actions too (AUTH-1, AUTH-6).',
    'csrf': 'There is no CSRF token; the session cookie is SameSite=Lax (AUTH-5).',
    'rate_limit': 'Nothing limits requests; put a reverse proxy in front for that.',
}


class ActionParser(BaseTagParser):
    """
    Parser for q:action statements.

    Examples:
        <q:action name="createUser" method="POST">
            <q:param name="email" type="email" required="true" />
            <q:query datasource="db">...</q:query>
            <q:redirect url="/users" flash="User created!" />
        </q:action>
    """

    @property
    def tag_names(self) -> List[str]:
        return ['action']

    def parse(self, element: ET.Element) -> ActionNode:
        """Parse q:action element"""
        name = element.get('name', '')
        method = element.get('method', 'POST')
        action_node = ActionNode(name, method)

        # AUTH-7: attributes that were parsed and never enforced. The worst
        # is require_auth="true": the action ran for anyone, while the page
        # read as protected. The docs promised csrf= and rate_limit= too.
        for attr, why in _NEVER_ENFORCED.items():
            if element.get(attr) is not None:
                from quantum.core.parser import QuantumParseError
                raise QuantumParseError(
                    f'<q:action name="{name}"> {attr}= is not supported: it was accepted '
                    f'and never enforced. {why}')

        # UI-10 (M17): the action's params come from a table's schema, read
        # from the database when the action is used; a q:param written wins.
        action_node.table = element.get('table')
        action_node.table_datasource = element.get('datasource')
        columns = element.get('columns')
        action_node.table_columns = [c.strip() for c in columns.split(',') if c.strip()] if columns else None
        if (action_node.table_datasource or columns) and not action_node.table:
            from quantum.core.parser import QuantumParseError
            raise QuantumParseError(
                f'<q:action name="{name}"> datasource= and columns= describe table=, which is missing')
        if action_node.table and not action_node.table_datasource:
            from quantum.core.parser import QuantumParseError
            raise QuantumParseError(
                f'<q:action name="{name}" table="{action_node.table}"> needs datasource= (where the table is)')

        # Parse children (params, statements)
        for child in element:
            child_type = self._get_element_name(child)

            if child_type == 'param':
                param = self.parse_param(child)
                action_node.add_param(param)
            else:
                # Parse other statements (query, set, redirect, etc.)
                statement = self.parse_child(child)
                if statement:
                    action_node.add_statement(statement)

        return action_node
