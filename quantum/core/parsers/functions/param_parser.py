"""
Param Parser - Parse q:param statements
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import QuantumParam


class ParamParser(BaseTagParser):
    """
    Parser for q:param statements.

    Examples:
        <q:param name="email" type="email" required="true" />
        <q:param name="password" type="string" minlength="8" />
        <q:param name="age" type="integer" min="0" max="150" />
    """

    @property
    def tag_names(self) -> List[str]:
        return ['param']

    def parse(self, element: ET.Element) -> QuantumParam:
        """Parse q:param element"""
        param = QuantumParam(
            name=element.get('name', ''),
            type=element.get('type', 'string'),
            required=element.get('required', 'false').lower() == 'true',
            default=element.get('default'),
            validation=element.get('validation'),
            description=element.get('description')
        )

        # REST-specific
        param.source = element.get('source', 'auto')

        # Validation
        param.validate_rule = element.get('validate')
        param.pattern = element.get('pattern')
        param.min = element.get('min')
        param.max = element.get('max')

        minlength_str = element.get('minlength')
        if minlength_str:
            try:
                param.minlength = int(minlength_str)
            except ValueError:
                pass

        maxlength_str = element.get('maxlength')
        if maxlength_str:
            try:
                param.maxlength = int(maxlength_str)
            except ValueError:
                pass

        param.range = element.get('range')
        param.enum = element.get('enum')

        # File upload
        param.maxsize = element.get('maxsize')
        param.accept = element.get('accept')

        return param
