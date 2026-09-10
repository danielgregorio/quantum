"""
Data Parser - Parse q:data statements

Handles data import from CSV, JSON, XML sources.
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser, ParserError
from quantum.core.ast_nodes import (
    DataNode, ColumnNode, FieldNode, TransformNode, HeaderNode,
    FilterNode, SortNode, LimitNode, ComputeNode,
)


class DataParser(BaseTagParser):
    """
    Parser for q:data statements.

    Supports:
    - CSV import with column definitions
    - JSON import with field mappings
    - XML import with XPath
    - Data transformations
    """

    @property
    def tag_names(self) -> List[str]:
        return ['data']

    def parse(self, element: ET.Element) -> DataNode:
        """
        Parse q:data statement.

        Args:
            element: XML element for q:data

        Returns:
            DataNode AST node
        """
        name = self.get_attr(element, 'name')
        source = self.get_attr(element, 'source')
        data_type = self.get_attr(element, 'type', 'csv')

        if not name:
            raise ParserError("Data requires 'name' attribute")
        if not source:
            raise ParserError("Data requires 'source' attribute")

        data_node = DataNode(name, source, data_type)

        # Caching
        data_node.cache = self.get_bool_attr(element, 'cache', True)
        data_node.ttl = self.get_int_attr(element, 'ttl', 0) or None

        # CSV attributes
        data_node.delimiter = self.get_attr(element, 'delimiter', ',')
        data_node.quote = self.get_attr(element, 'quote', '"')
        data_node.header = self.get_bool_attr(element, 'header', True)
        data_node.encoding = self.get_attr(element, 'encoding', 'utf-8')
        data_node.skip_rows = self.get_int_attr(element, 'skip_rows', 0)

        # XML attributes
        data_node.xpath = self.get_attr(element, 'xpath')
        data_node.namespace = self.get_attr(element, 'namespace')

        # Result
        data_node.result = self.get_attr(element, 'result')

        # Parse child elements
        for child in element:
            child_type = self.get_element_name(child)

            if child_type == 'column':
                column = self._parse_column(child)
                data_node.add_column(column)
            elif child_type == 'field':
                field = self._parse_field(child)
                data_node.add_field(field)
            elif child_type == 'transform':
                transform = self._parse_transform(child)
                data_node.add_transform(transform)
            elif child_type == 'header':
                header = self._parse_header(child)
                data_node.add_header(header)

        return data_node

    def _parse_column(self, element: ET.Element) -> ColumnNode:
        """Parse q:column for CSV."""
        name = self.get_attr(element, 'name')
        col_type = self.get_attr(element, 'type', 'string')

        if not name:
            raise ParserError("Column requires 'name' attribute")

        column = ColumnNode(name, col_type)
        column.required = self.get_bool_attr(element, 'required', False)
        column.default = self.get_attr(element, 'default')
        column.validate_rule = self.get_attr(element, 'validate')
        column.pattern = self.get_attr(element, 'pattern')

        # Numeric validation
        min_val = self.get_attr(element, 'min')
        if min_val:
            try:
                column.min = float(min_val)
            except ValueError:
                column.min = min_val

        max_val = self.get_attr(element, 'max')
        if max_val:
            try:
                column.max = float(max_val)
            except ValueError:
                column.max = max_val

        column.minlength = self.get_int_attr(element, 'minlength', 0) or None
        column.maxlength = self.get_int_attr(element, 'maxlength', 0) or None
        column.range = self.get_attr(element, 'range')
        column.enum = self.get_attr(element, 'enum')

        return column

    def _parse_field(self, element: ET.Element) -> FieldNode:
        """Parse q:field for JSON/XML."""
        name = self.get_attr(element, 'name')
        # `xpath` is the attribute every example and the reference use; only
        # `path` was read, so `xpath="@id"` became the name "id" and `type` was
        # dropped — attributes came back None and numbers came back as text.
        path = self.get_attr(element, 'xpath') or self.get_attr(element, 'path')

        if not name:
            raise ParserError("Field requires 'name' attribute")

        return FieldNode(name, path or name, self.get_attr(element, 'type') or 'string')

    def _parse_transform(self, element: ET.Element) -> TransformNode:
        """Parse q:transform — a container of operations.

        This read operation=/field=/value= off the tag and called
        TransformNode(operation, field, value). TransformNode takes NO
        arguments: it holds a list of child operations, which is also what
        the runtime iterates and what all four q:transform blocks in
        examples/ are written as:

            <q:transform>
              <q:filter condition="{active} == True" />
            </q:transform>

        So the parser rejected the only form anybody writes — "Transform
        requires 'operation' attribute" — and would have raised TypeError if
        it had ever got past that. Four example tests failed here.
        """
        transform_node = TransformNode()

        for child in element:
            tag = self._local_name(child.tag)

            if tag == 'filter':
                condition = self.get_attr(child, 'condition')
                if not condition:
                    raise ParserError("Filter requires 'condition' attribute")
                transform_node.add_operation(FilterNode(condition))

            elif tag == 'sort':
                by = self.get_attr(child, 'by') or self.get_attr(child, 'field')
                if not by:
                    raise ParserError("Sort requires 'by' attribute")
                order = (self.get_attr(child, 'order') or 'asc').lower()
                if order not in ('asc', 'desc'):
                    raise ParserError(
                        f"Invalid sort order: {order}. Must be 'asc' or 'desc'")
                transform_node.add_operation(SortNode(by, order))

            elif tag == 'limit':
                raw = self.get_attr(child, 'value') or self.get_attr(child, 'count')
                if raw is None or raw == '':
                    raise ParserError("Limit requires 'value' attribute")
                try:
                    limit = int(str(raw).strip())
                except ValueError:
                    raise ParserError(f"Limit value must be a number, got {raw!r}")
                transform_node.add_operation(LimitNode(limit))

            elif tag == 'compute':
                field = self.get_attr(child, 'field') or self.get_attr(child, 'name')
                expression = self.get_attr(child, 'expression')
                if not field:
                    raise ParserError("Compute requires 'field' attribute")
                if not expression:
                    raise ParserError("Compute requires 'expression' attribute")
                transform_node.add_operation(ComputeNode(
                    field, expression, self.get_attr(child, 'type') or 'string'))

            else:
                raise ParserError(
                    f"Unknown transform operation 'q:{tag}'. Supported: "
                    f"filter, sort, limit, compute")

        return transform_node

    @staticmethod
    def _local_name(tag: str) -> str:
        """'{ns}filter' or 'q:filter' -> 'filter'."""
        if '}' in tag:
            tag = tag.split('}', 1)[1]
        if ':' in tag:
            tag = tag.split(':', 1)[1]
        return tag

    def _parse_header(self, element: ET.Element) -> HeaderNode:
        """Parse q:header for HTTP headers."""
        name = self.get_attr(element, 'name')
        value = self.get_attr(element, 'value')

        if not name:
            raise ParserError("Header requires 'name' attribute")

        return HeaderNode(name, value or '')
