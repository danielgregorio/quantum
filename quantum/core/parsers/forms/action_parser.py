"""
Action Parser - Parse q:action statements for form handling
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import ActionNode


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

        # Parse optional attributes
        if element.get('csrf') == 'false':
            action_node.validate_csrf = False
        if element.get('rate_limit'):
            action_node.rate_limit = element.get('rate_limit')
        if element.get('require_auth') == 'true':
            action_node.require_auth = True

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
