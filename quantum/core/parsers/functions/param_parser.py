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
            description=element.get('description')
        )
        if element.get('validation') is not None:
            # A2: accepted and never read. The rules are validate=, type=,
            # pattern=, min/max, minlength/maxlength and enum=.
            from quantum.core.parser import QuantumParseError
            raise QuantumParseError(
                f'<q:param name="{element.get("name", "")}"> validation= is not supported: it was '
                f'accepted and never did anything. Use type=, pattern=, min/max, '
                f'minlength/maxlength or enum=.')

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
        check_upload_rules(element, param)
        from quantum.runtime.param_validation import check_param_type
        check_param_type(f'<q:param name="{param.name}">', element.get('type'), element=element)

        return param


def check_upload_rules(element: ET.Element, param) -> None:
    """FILE-1: maxsize= is a size; maxSize= (never read) is refused."""
    import re
    from quantum.core.parser import QuantumParseError
    if element.get('maxSize') is not None:
        raise QuantumParseError(f'<q:param name="{param.name}">: the attribute is maxsize, not maxSize')
    if param.maxsize is not None and not re.fullmatch(r'\s*\d+(\.\d+)?\s*(B|KB|MB|GB)?\s*',
                                                      param.maxsize, re.IGNORECASE):
        raise QuantumParseError(f'<q:param name="{param.name}" maxsize="{param.maxsize}">: '
                                f'a size like 500KB, 5MB or 1GB (FILE-1)')
