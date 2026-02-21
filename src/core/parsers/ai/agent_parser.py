"""
Agent Parser - Parse q:agent statements

Handles AI agent configuration with tools.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.features.agents.src.ast_node import (
    AgentNode, AgentToolNode, AgentToolParamNode,
    AgentInstructionNode, AgentExecuteNode
)


class AgentParser(BaseTagParser):
    """
    Parser for q:agent statements.

    Supports:
    - Tool definitions
    - System instructions
    - Execute configuration
    - Multiple providers
    """

    @property
    def tag_names(self) -> List[str]:
        return ['agent']

    def parse(self, element: ET.Element) -> AgentNode:
        """
        Parse q:agent statement.

        Args:
            element: XML element for q:agent

        Returns:
            AgentNode AST node
        """
        name = self.get_attr(element, 'name')

        if not name:
            raise ParserError("Agent requires 'name' attribute")

        agent_node = AgentNode(
            name=name,
            model=self.get_attr(element, 'model', 'phi3'),
            endpoint=self.get_attr(element, 'endpoint', ''),
            provider=self.get_attr(element, 'provider', 'auto'),
            api_key=self.get_attr(element, 'apiKey', ''),
            max_iterations=self.get_int_attr(element, 'maxIterations', 10),
            timeout=self.get_int_attr(element, 'timeout', 60000)
        )

        # Parse children
        for child in element:
            child_type = self.get_element_name(child)

            if child_type == 'instruction':
                agent_node.instruction = AgentInstructionNode(
                    content=self.get_text(child)
                )
            elif child_type == 'tool':
                tool = self._parse_tool(child)
                agent_node.tools.append(tool)
            elif child_type == 'execute':
                agent_node.execute = AgentExecuteNode(
                    task=self.get_attr(child, 'task', self.get_text(child)),
                    context=self.get_attr(child, 'context', ''),
                    entry=self.get_attr(child, 'entry', '')
                )

        return agent_node

    def _parse_tool(self, element: ET.Element) -> AgentToolNode:
        """Parse q:tool within q:agent."""
        name = self.get_attr(element, 'name')
        description = self.get_attr(element, 'description', '')
        builtin = self.get_bool_attr(element, 'builtin', False)

        tool = AgentToolNode(
            name=name,
            description=description,
            builtin=builtin
        )

        # Parse params and body
        for child in element:
            child_type = self.get_element_name(child)

            if child_type == 'param':
                param = AgentToolParamNode(
                    name=self.get_attr(child, 'name', ''),
                    type=self.get_attr(child, 'type', 'string'),
                    required=self.get_bool_attr(child, 'required', False),
                    description=self.get_attr(child, 'description', '')
                )
                tool.params.append(param)
            else:
                # Tool body statement
                statement = self.parse_statement(child)
                if statement:
                    tool.body.append(statement)

        return tool
