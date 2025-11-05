"""
Data Import Feature - Runtime
Handles execution of all data import and transformation operations
"""

import time
import json
import csv
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from io import StringIO
import re


@dataclass
class DataResult:
    """Result object for all data operations"""
    success: bool
    data: Any = None
    error: Optional[Dict[str, Any]] = None
    recordCount: int = 0
    loadTime: float = 0.0
    cached: bool = False
    source: str = ""


class DataImportService:
    """Service to handle all types of data import and transformation"""

    def __init__(self):
        self.cache: Dict[str, Any] = {}  # Simple in-memory cache

    def import_data(
        self,
        data_type: str,
        source: str,
        params: Dict[str, Any],
        context: Any = None
    ) -> DataResult:
        """Main data import dispatcher"""
        start_time = time.time()

        try:
            # Check cache if enabled
            cache_enabled = params.get('cache', True)
            if cache_enabled:
                cache_key = f"data_{source}_{hash(str(params))}"
                cached_result = self.get_from_cache(cache_key)
                if cached_result is not None:
                    cached_result.cached = True
                    return cached_result

            # Dispatch based on type
            if data_type == "csv":
                result = self._import_csv(source, params)
            elif data_type == "json":
                result = self._import_json(source, params)
            elif data_type == "xml":
                result = self._import_xml(source, params)
            elif data_type == "transform":
                result = self._transform_data(source, params, context)
            else:
                return DataResult(
                    success=False,
                    error={"message": f"Unknown data type: {data_type}"},
                    source=source
                )

            # Calculate load time
            load_time = (time.time() - start_time) * 1000  # Convert to ms
            result.loadTime = load_time

            # Apply transformations if specified
            if 'transforms' in params and params['transforms']:
                result = self._apply_transformations(result, params['transforms'], context)

            # Cache result if enabled
            if cache_enabled and result.success:
                ttl = params.get('ttl')
                self.put_in_cache(cache_key, result, ttl)

            return result

        except Exception as e:
            load_time = (time.time() - start_time) * 1000
            return DataResult(
                success=False,
                error={
                    "message": str(e),
                    "type": type(e).__name__
                },
                loadTime=load_time,
                source=source
            )

    def _import_csv(self, source: str, params: Dict[str, Any]) -> DataResult:
        """Import CSV data from file or URL"""
        try:
            # Get CSV content
            content = self._get_source_content(source, params.get('headers', []))

            # Parse CSV
            delimiter = params.get('delimiter', ',')
            quote = params.get('quote', '"')
            has_header = params.get('header', True)
            encoding = params.get('encoding', 'utf-8')
            skip_rows = params.get('skip_rows', 0)
            columns = params.get('columns', [])

            # Parse CSV content
            csv_reader = csv.DictReader(
                StringIO(content),
                delimiter=delimiter,
                quotechar=quote
            ) if has_header else csv.reader(StringIO(content), delimiter=delimiter, quotechar=quote)

            # Skip rows if needed
            for _ in range(skip_rows):
                try:
                    next(csv_reader)
                except StopIteration:
                    break

            # Convert to list of dictionaries
            data = []
            for row in csv_reader:
                if has_header:
                    # Row is already a dict
                    record = self._convert_csv_row(row, columns)
                else:
                    # Row is a list - create dict from column definitions
                    if columns:
                        record = {}
                        for i, col_def in enumerate(columns):
                            if i < len(row):
                                col_name = col_def.get('name')
                                col_value = row[i]
                                record[col_name] = self._convert_type(col_value, col_def.get('type', 'string'))
                    else:
                        # No columns defined - use numeric keys
                        record = {str(i): val for i, val in enumerate(row)}

                data.append(record)

            return DataResult(
                success=True,
                data=data,
                recordCount=len(data),
                source=source
            )

        except Exception as e:
            return DataResult(
                success=False,
                error={
                    "message": f"CSV import failed: {str(e)}",
                    "type": type(e).__name__
                },
                source=source
            )

    def _import_json(self, source: str, params: Dict[str, Any]) -> DataResult:
        """Import JSON data from file or URL"""
        try:
            # Get JSON content
            content = self._get_source_content(source, params.get('headers', []))

            # Parse JSON
            data = json.loads(content)

            # Ensure data is a list
            if not isinstance(data, list):
                # If it's a dict, wrap it in a list
                data = [data]

            return DataResult(
                success=True,
                data=data,
                recordCount=len(data) if isinstance(data, list) else 1,
                source=source
            )

        except json.JSONDecodeError as e:
            return DataResult(
                success=False,
                error={
                    "message": f"Invalid JSON: {str(e)}",
                    "type": "JSONDecodeError"
                },
                source=source
            )
        except Exception as e:
            return DataResult(
                success=False,
                error={
                    "message": f"JSON import failed: {str(e)}",
                    "type": type(e).__name__
                },
                source=source
            )

    def _import_xml(self, source: str, params: Dict[str, Any]) -> DataResult:
        """Import XML data from file or URL with XPath"""
        try:
            # Get XML content
            content = self._get_source_content(source, params.get('headers', []))

            # Parse XML
            root = ET.fromstring(content)

            # Get XPath expression
            xpath = params.get('xpath', '.')
            fields = params.get('fields', [])

            # Find nodes using XPath (basic support - ET has limited XPath)
            nodes = root.findall(xpath)

            # Extract data from nodes
            data = []
            for node in nodes:
                record = {}
                for field_def in fields:
                    field_name = field_def.get('name')
                    field_xpath = field_def.get('xpath')
                    field_type = field_def.get('type', 'string')

                    # Extract value using XPath
                    value = self._extract_xml_value(node, field_xpath)
                    record[field_name] = self._convert_type(value, field_type)

                data.append(record)

            return DataResult(
                success=False,
                data=data,
                recordCount=len(data),
                source=source
            )

        except ET.ParseError as e:
            return DataResult(
                success=False,
                error={
                    "message": f"Invalid XML: {str(e)}",
                    "type": "XMLParseError"
                },
                source=source
            )
        except Exception as e:
            return DataResult(
                success=False,
                error={
                    "message": f"XML import failed: {str(e)}",
                    "type": type(e).__name__
                },
                source=source
            )

    def _transform_data(self, source: str, params: Dict[str, Any], context: Any) -> DataResult:
        """Transform existing data (from variable reference)"""
        try:
            # Source should be a variable reference like "{users}"
            # Extract variable name and get data from context
            if source.startswith('{') and source.endswith('}'):
                var_name = source[1:-1]  # Remove braces
            else:
                var_name = source

            # Get data from context
            if hasattr(context, 'get_variable'):
                data = context.get_variable(var_name)
            elif isinstance(context, dict):
                data = context.get(var_name)
            else:
                return DataResult(
                    success=False,
                    error={"message": f"Cannot access variable '{var_name}' from context"},
                    source=source
                )

            if data is None:
                return DataResult(
                    success=False,
                    error={"message": f"Variable '{var_name}' not found"},
                    source=source
                )

            # Ensure data is a list
            if not isinstance(data, list):
                data = [data]

            return DataResult(
                success=True,
                data=data,
                recordCount=len(data),
                source=source
            )

        except Exception as e:
            return DataResult(
                success=False,
                error={
                    "message": f"Transform failed: {str(e)}",
                    "type": type(e).__name__
                },
                source=source
            )

    def _apply_transformations(self, result: DataResult, transforms: List[Dict[str, Any]], context: Any) -> DataResult:
        """Apply transformation operations to data"""
        if not result.success or not result.data:
            return result

        data = result.data

        for transform_op in transforms:
            op_type = transform_op.get('type')

            if op_type == 'filter':
                data = self._apply_filter(data, transform_op, context)
            elif op_type == 'sort':
                data = self._apply_sort(data, transform_op)
            elif op_type == 'limit':
                data = self._apply_limit(data, transform_op)
            elif op_type == 'compute':
                data = self._apply_compute(data, transform_op, context)

        # Update result
        result.data = data
        result.recordCount = len(data)
        return result

    def _apply_filter(self, data: List[Dict[str, Any]], filter_op: Dict[str, Any], context: Any) -> List[Dict[str, Any]]:
        """Filter data based on condition"""
        condition = filter_op.get('condition', '')

        filtered = []
        for record in data:
            # Evaluate condition for this record
            if self._evaluate_condition(condition, record, context):
                filtered.append(record)

        return filtered

    def _apply_sort(self, data: List[Dict[str, Any]], sort_op: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Sort data by field"""
        by_field = sort_op.get('by')
        order = sort_op.get('order', 'asc')

        if not by_field:
            return data

        try:
            # Sort data
            reverse = (order == 'desc')
            sorted_data = sorted(data, key=lambda x: x.get(by_field, ''), reverse=reverse)
            return sorted_data
        except Exception:
            # If sorting fails, return original data
            return data

    def _apply_limit(self, data: List[Dict[str, Any]], limit_op: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Limit number of records"""
        limit = limit_op.get('value', 0)

        if isinstance(limit, str):
            try:
                limit = int(limit)
            except ValueError:
                return data

        return data[:limit]

    def _apply_compute(self, data: List[Dict[str, Any]], compute_op: Dict[str, Any], context: Any) -> List[Dict[str, Any]]:
        """Compute derived field"""
        field = compute_op.get('field')
        expression = compute_op.get('expression')
        comp_type = compute_op.get('type', 'string')

        if not field or not expression:
            return data

        # Add computed field to each record
        for record in data:
            value = self._evaluate_expression(expression, record, context)
            record[field] = self._convert_type(value, comp_type)

        return data

    def _get_source_content(self, source: str, headers: List[Dict[str, str]] = None) -> str:
        """Get content from file or URL"""
        # Check if source is a URL
        if source.startswith('http://') or source.startswith('https://'):
            # Fetch from URL
            headers_dict = {}
            if headers:
                for header in headers:
                    headers_dict[header.get('name')] = header.get('value')

            response = requests.get(source, headers=headers_dict, timeout=30)
            response.raise_for_status()
            return response.text
        else:
            # Read from file
            file_path = Path(source)
            if not file_path.is_absolute():
                # Relative path - resolve from current working directory
                file_path = Path.cwd() / file_path

            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()

    def _convert_csv_row(self, row: Dict[str, str], columns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert CSV row values to proper types"""
        if not columns:
            return row

        converted = {}
        for col_def in columns:
            col_name = col_def.get('name')
            col_type = col_def.get('type', 'string')

            if col_name in row:
                converted[col_name] = self._convert_type(row[col_name], col_type)

        # Include any columns not defined in schema
        for key, value in row.items():
            if key not in converted:
                converted[key] = value

        return converted

    def _convert_type(self, value: Any, target_type: str) -> Any:
        """Convert value to target type"""
        if value is None or value == '':
            return None

        try:
            if target_type == 'integer':
                return int(value)
            elif target_type == 'decimal':
                return float(value)
            elif target_type == 'boolean':
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                return bool(value)
            elif target_type == 'json':
                if isinstance(value, str):
                    return json.loads(value)
                return value
            elif target_type == 'array':
                if isinstance(value, list):
                    return value
                if isinstance(value, str):
                    return json.loads(value)
                return [value]
            else:  # string
                return str(value)
        except (ValueError, json.JSONDecodeError):
            return value

    def _extract_xml_value(self, node: ET.Element, xpath: str) -> Optional[str]:
        """Extract value from XML node using XPath"""
        # Handle attribute access (@attr)
        if xpath.startswith('@'):
            attr_name = xpath[1:]
            return node.get(attr_name)

        # Handle text content (text())
        if xpath == 'text()':
            return node.text

        # Handle child element
        child = node.find(xpath)
        if child is not None:
            if xpath.endswith('/text()'):
                return child.text
            elif xpath.endswith('/@'):
                # Extract attribute from child
                parts = xpath.rsplit('/@', 1)
                if len(parts) == 2:
                    child_path, attr = parts
                    child_elem = node.find(child_path)
                    if child_elem is not None:
                        return child_elem.get(attr)
            else:
                return child.text

        return None

    def _evaluate_condition(self, condition: str, record: Dict[str, Any], context: Any) -> bool:
        """Evaluate filter condition (basic implementation)"""
        # Replace {field} with actual values
        expr = condition
        for key, value in record.items():
            placeholder = f"{{{key}}}"
            if placeholder in expr:
                # Quote strings, leave numbers as-is
                if isinstance(value, str):
                    expr = expr.replace(placeholder, f"'{value}'")
                else:
                    expr = expr.replace(placeholder, str(value))

        try:
            # Evaluate as Python expression (basic - should be improved with safe eval)
            result = eval(expr)
            return bool(result)
        except Exception:
            return False

    def _evaluate_expression(self, expression: str, record: Dict[str, Any], context: Any) -> Any:
        """Evaluate expression for computed field"""
        # Replace {field} with actual values
        expr = expression
        for key, value in record.items():
            placeholder = f"{{{key}}}"
            if placeholder in expr:
                if isinstance(value, str):
                    expr = expr.replace(placeholder, f"'{value}'")
                else:
                    expr = expr.replace(placeholder, str(value))

        try:
            # Evaluate as Python expression
            result = eval(expr)
            return result
        except Exception:
            return None

    def get_from_cache(self, cache_key: str) -> Optional[DataResult]:
        """Get value from cache"""
        return self.cache.get(cache_key)

    def put_in_cache(self, cache_key: str, value: DataResult, ttl: Optional[int] = None):
        """Put value in cache"""
        # Simple implementation - in production you'd use TTL properly
        self.cache[cache_key] = value

    def clear_cache(self):
        """Clear all cache"""
        self.cache.clear()
