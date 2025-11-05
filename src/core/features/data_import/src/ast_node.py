"""
Data Import Feature - AST Nodes
Defines DataNode and related nodes for q:data
"""

from typing import List, Dict, Any, Optional
from core.ast_nodes import QuantumNode


class DataNode(QuantumNode):
    """Represents a <q:data> - Data import and transformation component"""

    def __init__(self, name: str, source: str, data_type: str):
        self.name = name              # Variable name for result
        self.source = source          # File path, URL, or variable reference
        self.data_type = data_type    # csv, json, xml, transform

        # Caching
        self.cache = True             # Cache by default
        self.ttl = None               # Cache TTL in seconds

        # CSV-specific attributes
        self.delimiter = ","
        self.quote = '"'
        self.header = True            # First row contains headers
        self.encoding = "utf-8"
        self.skip_rows = 0

        # XML-specific attributes
        self.xpath = None             # XPath expression to select nodes
        self.namespace = None         # XML namespace URI

        # Child elements
        self.columns: List['ColumnNode'] = []          # For CSV
        self.fields: List['FieldNode'] = []            # For XML
        self.transforms: List['TransformNode'] = []    # For transformations
        self.headers: List['HeaderNode'] = []          # For HTTP headers (URL sources)

        # Result metadata
        self.result = None            # Variable name for metadata

    def add_column(self, column: 'ColumnNode'):
        """Add CSV column definition"""
        self.columns.append(column)

    def add_field(self, field: 'FieldNode'):
        """Add XML field mapping"""
        self.fields.append(field)

    def add_transform(self, transform: 'TransformNode'):
        """Add transformation operation"""
        self.transforms.append(transform)

    def add_header(self, header: 'HeaderNode'):
        """Add HTTP header"""
        self.headers.append(header)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "data",
            "name": self.name,
            "source": self.source,
            "data_type": self.data_type,
            "cache": self.cache,
            "ttl": self.ttl,
            "columns": [c.to_dict() for c in self.columns],
            "fields": [f.to_dict() for f in self.fields],
            "transforms": [t.to_dict() for t in self.transforms],
            "headers": [h.to_dict() for h in self.headers]
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Data name is required")
        if not self.source:
            errors.append("Data source is required")
        if self.data_type not in ['csv', 'json', 'xml', 'transform']:
            errors.append(f"Invalid data type: {self.data_type}. Must be csv, json, xml, or transform")

        # Validate child elements
        for column in self.columns:
            errors.extend(column.validate())
        for field in self.fields:
            errors.extend(field.validate())
        for transform in self.transforms:
            errors.extend(transform.validate())
        for header in self.headers:
            errors.extend(header.validate())

        return errors


class ColumnNode(QuantumNode):
    """Represents a <q:column> - CSV column definition"""

    def __init__(self, name: str, col_type: str = "string"):
        self.name = name
        self.col_type = col_type      # string, integer, decimal, boolean, date, datetime

        # Validation (same as QuantumParam)
        self.required = False
        self.default = None
        self.validate_rule = None
        self.pattern = None
        self.min = None
        self.max = None
        self.minlength = None
        self.maxlength = None
        self.range = None
        self.enum = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "column",
            "name": self.name,
            "col_type": self.col_type,
            "required": self.required,
            "default": self.default
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Column name is required")
        valid_types = ['string', 'integer', 'decimal', 'boolean', 'date', 'datetime', 'json', 'array']
        if self.col_type not in valid_types:
            errors.append(f"Invalid column type: {self.col_type}. Must be one of {valid_types}")
        return errors


class FieldNode(QuantumNode):
    """Represents a <q:field> - XML field mapping"""

    def __init__(self, name: str, xpath: str, field_type: str = "string"):
        self.name = name
        self.xpath = xpath            # XPath expression to extract value
        self.field_type = field_type  # string, integer, decimal, boolean, date, datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "field",
            "name": self.name,
            "xpath": self.xpath,
            "field_type": self.field_type
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Field name is required")
        if not self.xpath:
            errors.append("Field xpath is required")
        valid_types = ['string', 'integer', 'decimal', 'boolean', 'date', 'datetime', 'json', 'array']
        if self.field_type not in valid_types:
            errors.append(f"Invalid field type: {self.field_type}. Must be one of {valid_types}")
        return errors


class TransformNode(QuantumNode):
    """Represents a <q:transform> - Container for transformation operations"""

    def __init__(self):
        self.operations: List[QuantumNode] = []  # Filter, Sort, Limit, Compute, etc.

    def add_operation(self, operation: QuantumNode):
        """Add transformation operation"""
        self.operations.append(operation)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "transform",
            "operations": [op.to_dict() for op in self.operations]
        }

    def validate(self) -> List[str]:
        errors = []
        for operation in self.operations:
            errors.extend(operation.validate())
        return errors


class FilterNode(QuantumNode):
    """Represents a <q:filter> - Filter operation"""

    def __init__(self, condition: str):
        self.condition = condition    # Filter expression

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "filter",
            "condition": self.condition
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.condition:
            errors.append("Filter condition is required")
        return errors


class SortNode(QuantumNode):
    """Represents a <q:sort> - Sort operation"""

    def __init__(self, by: str, order: str = "asc"):
        self.by = by                  # Field name to sort by
        self.order = order            # asc or desc

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "sort",
            "by": self.by,
            "order": self.order
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.by:
            errors.append("Sort 'by' field is required")
        if self.order not in ['asc', 'desc']:
            errors.append(f"Invalid sort order: {self.order}. Must be 'asc' or 'desc'")
        return errors


class LimitNode(QuantumNode):
    """Represents a <q:limit> - Limit operation"""

    def __init__(self, value: int):
        self.value = value            # Maximum number of records

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "limit",
            "value": self.value
        }

    def validate(self) -> List[str]:
        errors = []
        if self.value is None:
            errors.append("Limit value is required")
        if isinstance(self.value, int) and self.value < 0:
            errors.append("Limit value must be >= 0")
        return errors


class ComputeNode(QuantumNode):
    """Represents a <q:compute> - Compute derived field"""

    def __init__(self, field: str, expression: str, comp_type: str = "string"):
        self.field = field            # New field name
        self.expression = expression  # Expression to compute value
        self.comp_type = comp_type    # Result type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "compute",
            "field": self.field,
            "expression": self.expression,
            "comp_type": self.comp_type
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.field:
            errors.append("Compute field name is required")
        if not self.expression:
            errors.append("Compute expression is required")
        return errors


class HeaderNode(QuantumNode):
    """Represents a <q:header> - HTTP header for URL sources"""

    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "header",
            "name": self.name,
            "value": self.value[:50] + "..." if len(str(self.value)) > 50 else self.value
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Header name is required")
        if self.value is None:
            errors.append(f"Header '{self.name}' value is required")
        return errors
