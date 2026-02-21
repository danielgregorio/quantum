"""
Schedule Parser - Parse q:schedule statements

Handles scheduled task configuration.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.ast_nodes import ScheduleNode


class ScheduleParser(BaseTagParser):
    """
    Parser for q:schedule statements.

    Supports:
    - Interval scheduling
    - Cron expressions
    - One-time execution
    - Timezone support
    """

    @property
    def tag_names(self) -> List[str]:
        return ['schedule']

    def parse(self, element: ET.Element) -> ScheduleNode:
        """
        Parse q:schedule statement.

        Args:
            element: XML element for q:schedule

        Returns:
            ScheduleNode AST node
        """
        name = self.get_attr(element, 'name')

        if not name:
            raise ParserError("Schedule requires 'name' attribute")

        schedule_node = ScheduleNode(
            name=name,
            action=self.get_attr(element, 'action', 'run'),
            interval=self.get_attr(element, 'interval'),
            cron=self.get_attr(element, 'cron'),
            at=self.get_attr(element, 'at'),
            timezone=self.get_attr(element, 'timezone', 'UTC'),
            retry=self.get_int_attr(element, 'retry', 3),
            timeout=self.get_attr(element, 'timeout'),
            overlap=self.get_bool_attr(element, 'overlap', False),
            enabled=self.get_bool_attr(element, 'enabled', True)
        )

        # Parse body statements
        for child in element:
            statement = self.parse_statement(child)
            if statement:
                schedule_node.add_statement(statement)

        return schedule_node
