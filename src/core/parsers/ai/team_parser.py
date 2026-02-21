"""
Team Parser - Parse q:team statements

Handles multi-agent team configuration.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.features.agents.src.ast_node import AgentTeamNode, AgentExecuteNode


class TeamParser(BaseTagParser):
    """
    Parser for q:team statements.

    Supports:
    - Multiple agent definitions
    - Shared context
    - Supervisor/entry configuration
    """

    @property
    def tag_names(self) -> List[str]:
        return ['team']

    def parse(self, element: ET.Element) -> AgentTeamNode:
        """
        Parse q:team statement.

        Args:
            element: XML element for q:team

        Returns:
            AgentTeamNode AST node
        """
        name = self.get_attr(element, 'name')

        if not name:
            raise ParserError("Team requires 'name' attribute")

        team_node = AgentTeamNode(
            name=name,
            supervisor=self.get_attr(element, 'supervisor', ''),
            max_handoffs=self.get_int_attr(element, 'maxHandoffs', 10),
            max_total_iterations=self.get_int_attr(element, 'maxTotalIterations', 50)
        )

        # Parse children
        for child in element:
            child_type = self.get_element_name(child)

            if child_type == 'shared':
                # Parse shared context (q:set nodes)
                for shared_child in child:
                    statement = self.parse_statement(shared_child)
                    if statement:
                        team_node.shared.append(statement)
            elif child_type == 'agent':
                # Parse agent using main parser
                agent = self.parse_statement(child)
                if agent:
                    team_node.agents.append(agent)
            elif child_type == 'execute':
                team_node.execute = AgentExecuteNode(
                    task=self.get_attr(child, 'task', self.get_text(child)),
                    context=self.get_attr(child, 'context', ''),
                    entry=self.get_attr(child, 'entry', '')
                )

        return team_node
