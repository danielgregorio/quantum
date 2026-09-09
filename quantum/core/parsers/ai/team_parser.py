"""
Team Parser - Parse q:team statements

Handles multi-agent team configuration.
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser, ParserError
from quantum.core.features.agents.src.ast_node import AgentTeamNode, AgentExecuteNode


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

        # Create team node with defaults (matching legacy behavior)
        team_node = AgentTeamNode(name=name)

        # Parse attributes (support both snake_case and camelCase)
        team_node.supervisor = self.get_attr(element, 'supervisor', '')

        max_handoffs = self.get_attr(element, 'max_handoffs') or self.get_attr(element, 'maxHandoffs')
        if max_handoffs:
            try:
                team_node.max_handoffs = int(max_handoffs)
            except ValueError:
                pass

        max_iterations = self.get_attr(element, 'max_total_iterations') or self.get_attr(element, 'maxTotalIterations')
        if max_iterations:
            try:
                team_node.max_total_iterations = int(max_iterations)
            except ValueError:
                pass

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
                    # Team members are driven by the team's <q:execute>, not
                    # one of their own — mark them so validate() doesn't
                    # reject the whole component.
                    agent.in_team = True
                    team_node.agents.append(agent)
            elif child_type == 'execute':
                team_node.execute = AgentExecuteNode(
                    task=self.get_attr(child, 'task', self.get_text(child)),
                    context=self.get_attr(child, 'context', ''),
                    entry=self.get_attr(child, 'entry', '')
                )

        return team_node
