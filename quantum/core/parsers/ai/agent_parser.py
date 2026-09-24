"""
Agent Parser - Parse q:agent statements

Handles AI agent configuration with tools.
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser, ParserError
from quantum.core.features.agents.src.ast_node import (
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
        if element.get('max_iterations') is not None:
            # The guide and the README wrote max_iterations; it was never read
            # and every agent ran up to 10 steps.
            raise ParserError(f'<q:agent name="{name}">: the attribute is maxIterations, '
                              f'not max_iterations')
        on_error = self.get_attr(element, 'onerror', 'fail')
        if on_error not in ('fail', 'continue'):
            raise ParserError(f'<q:agent name="{name}"> onerror must be "fail" or "continue", '
                              f'not "{on_error}"')

        agent_node = AgentNode(
            name=name,
            # Undeclared, the configured model (IA-1) — resolved when the agent runs.
            model=self.get_attr(element, 'model'),
            endpoint=self.get_attr(element, 'endpoint', ''),
            provider=self.get_attr(element, 'provider', 'auto'),
            api_key=self.get_attr(element, 'apiKey', ''),
            max_iterations=self.get_int_attr(element, 'maxIterations', 10),
            timeout=self.get_int_attr(element, 'timeout', 60000),
            on_error=on_error,
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
                from quantum.runtime.param_validation import check_param_type
                check_param_type(f'<q:tool> <q:param name="{self.get_attr(child, "name", "")}">',
                                 self.get_attr(child, 'type'), element=child)
                param = AgentToolParamNode(
                    name=self.get_attr(child, 'name', ''),
                    type=self.get_attr(child, 'type', 'string'),
                    required=self.get_bool_attr(child, 'required', False),
                    default=self.get_attr(child, 'default'),
                    description=self.get_attr(child, 'description', '')
                )
                tool.params.append(param)
            else:
                # Tool body statement
                statement = self.parse_statement(child)
                if statement:
                    tool.body.append(statement)

        return tool
