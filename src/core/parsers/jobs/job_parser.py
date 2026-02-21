"""
Job Parser - Parse q:job statements

Handles job queue configuration.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.ast_nodes import JobNode, QuantumParam


class JobParser(BaseTagParser):
    """
    Parser for q:job statements.

    Supports:
    - Job definition
    - Job dispatch
    - Batch dispatch
    - Retry configuration
    """

    @property
    def tag_names(self) -> List[str]:
        return ['job']

    def parse(self, element: ET.Element) -> JobNode:
        """
        Parse q:job statement.

        Args:
            element: XML element for q:job

        Returns:
            JobNode AST node
        """
        name = self.get_attr(element, 'name')

        if not name:
            raise ParserError("Job requires 'name' attribute")

        queue = self.get_attr(element, 'queue', 'default')
        action = self.get_attr(element, 'action', 'define')

        job_node = JobNode(name, queue, action)
        job_node.delay = self.get_attr(element, 'delay')
        job_node.priority = self.get_int_attr(element, 'priority', 0)
        job_node.attempts = self.get_int_attr(element, 'attempts', 3)
        job_node.backoff = self.get_attr(element, 'backoff', '30s')
        job_node.timeout = self.get_attr(element, 'timeout')

        # Parse children
        for child in element:
            child_type = self.get_element_name(child)

            if child_type == 'param':
                param = QuantumParam(
                    self.get_attr(child, 'name', ''),
                    self.get_attr(child, 'type', 'string')
                )
                param.value = self.get_attr(child, 'value')
                param.required = self.get_bool_attr(child, 'required', False)
                job_node.add_param(param)
            else:
                # Job body statement
                statement = self.parse_statement(child)
                if statement:
                    job_node.add_statement(statement)

        return job_node
