"""
Quantum Query Validators - Type validation and conversion for query parameters
"""

from typing import Any, Tuple, Optional
from datetime import datetime, date, time as datetime_time
import json


class QueryValidationError(Exception):
    """Raised when query parameter validation fails"""
    pass


class QueryValidator:
    """Validates and converts query parameters"""

    @staticmethod
    def validate_param(value: Any, param_type: str, attributes: dict) -> Any:
        """
        Validate and convert parameter value

        Args:
            value: Parameter value
            param_type: Parameter type (string, integer, decimal, boolean, datetime, etc.)
            attributes: Additional constraints (maxLength, scale, null)

        Returns:
            Converted and validated value

        Raises:
            QueryValidationError: If validation fails
        """
        # Check null
        null_allowed = attributes.get('null', False)
        if value is None:
            if not null_allowed:
                raise QueryValidationError("Parameter cannot be null")
            return None

        # Convert based on type
        try:
            if param_type == 'string':
                return QueryValidator._validate_string(value, attributes)
            elif param_type == 'integer':
                return QueryValidator._validate_integer(value, attributes)
            elif param_type == 'decimal':
                return QueryValidator._validate_decimal(value, attributes)
            elif param_type == 'boolean':
                return QueryValidator._validate_boolean(value, attributes)
            elif param_type == 'datetime':
                return QueryValidator._validate_datetime(value, attributes)
            elif param_type == 'date':
                return QueryValidator._validate_date(value, attributes)
            elif param_type == 'time':
                return QueryValidator._validate_time(value, attributes)
            elif param_type == 'array':
                return QueryValidator._validate_array(value, attributes)
            elif param_type == 'json':
                return QueryValidator._validate_json(value, attributes)
            else:
                raise QueryValidationError(f"Unknown parameter type: {param_type}")

        except QueryValidationError:
            raise
        except Exception as e:
            raise QueryValidationError(f"Validation error: {e}")

    @staticmethod
    def _validate_string(value: Any, attributes: dict) -> str:
        """Validate and convert to string"""
        str_value = str(value)

        # Check maxLength
        max_length = attributes.get('max_length')
        if max_length and len(str_value) > max_length:
            raise QueryValidationError(
                f"String length {len(str_value)} exceeds maximum {max_length}"
            )

        return str_value

    @staticmethod
    def _validate_integer(value: Any, attributes: dict) -> int:
        """Validate and convert to integer"""
        if isinstance(value, int):
            return value

        if isinstance(value, str):
            # Remove whitespace
            value = value.strip()

        try:
            return int(value)
        except (ValueError, TypeError):
            raise QueryValidationError(f"Cannot convert '{value}' to integer")

    @staticmethod
    def _validate_decimal(value: Any, attributes: dict) -> float:
        """Validate and convert to decimal (float)"""
        if isinstance(value, (int, float)):
            float_value = float(value)
        elif isinstance(value, str):
            try:
                float_value = float(value.strip())
            except ValueError:
                raise QueryValidationError(f"Cannot convert '{value}' to decimal")
        else:
            raise QueryValidationError(f"Cannot convert '{value}' to decimal")

        # Apply scale if specified
        scale = attributes.get('scale')
        if scale is not None:
            float_value = round(float_value, scale)

        return float_value

    @staticmethod
    def _validate_boolean(value: Any, attributes: dict) -> bool:
        """Validate and convert to boolean"""
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            value_lower = value.strip().lower()
            if value_lower in ['true', '1', 'yes', 'on']:
                return True
            elif value_lower in ['false', '0', 'no', 'off']:
                return False
            else:
                raise QueryValidationError(f"Cannot convert '{value}' to boolean")

        if isinstance(value, (int, float)):
            return bool(value)

        raise QueryValidationError(f"Cannot convert '{value}' to boolean")

    @staticmethod
    def _validate_datetime(value: Any, attributes: dict) -> datetime:
        """Validate and convert to datetime"""
        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            # Try common datetime formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S.%fZ',
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(value.strip(), fmt)
                except ValueError:
                    continue

            raise QueryValidationError(
                f"Cannot parse datetime '{value}'. Expected format: YYYY-MM-DD HH:MM:SS"
            )

        raise QueryValidationError(f"Cannot convert '{value}' to datetime")

    @staticmethod
    def _validate_date(value: Any, attributes: dict) -> date:
        """Validate and convert to date"""
        if isinstance(value, date):
            return value

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            # Try common date formats
            formats = ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y']

            for fmt in formats:
                try:
                    return datetime.strptime(value.strip(), fmt).date()
                except ValueError:
                    continue

            raise QueryValidationError(
                f"Cannot parse date '{value}'. Expected format: YYYY-MM-DD"
            )

        raise QueryValidationError(f"Cannot convert '{value}' to date")

    @staticmethod
    def _validate_time(value: Any, attributes: dict) -> datetime_time:
        """Validate and convert to time"""
        if isinstance(value, datetime_time):
            return value

        if isinstance(value, datetime):
            return value.time()

        if isinstance(value, str):
            # Try common time formats
            formats = ['%H:%M:%S', '%H:%M:%S.%f', '%H:%M']

            for fmt in formats:
                try:
                    return datetime.strptime(value.strip(), fmt).time()
                except ValueError:
                    continue

            raise QueryValidationError(
                f"Cannot parse time '{value}'. Expected format: HH:MM:SS"
            )

        raise QueryValidationError(f"Cannot convert '{value}' to time")

    @staticmethod
    def _validate_array(value: Any, attributes: dict) -> list:
        """Validate and convert to array"""
        if isinstance(value, list):
            return value

        if isinstance(value, tuple):
            return list(value)

        if isinstance(value, str):
            # Try to parse as JSON
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
                else:
                    raise QueryValidationError("JSON value is not an array")
            except json.JSONDecodeError:
                # Try comma-separated values
                return [item.strip() for item in value.split(',')]

        raise QueryValidationError(f"Cannot convert '{value}' to array")

    @staticmethod
    def _validate_json(value: Any, attributes: dict) -> dict:
        """Validate and convert to JSON object"""
        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                raise QueryValidationError(f"Invalid JSON: {e}")

        raise QueryValidationError(f"Cannot convert '{value}' to JSON")

    @staticmethod
    def sanitize_sql(sql: str) -> str:
        """
        Basic SQL sanitization to prevent comment injection and other attacks

        Args:
            sql: SQL query string

        Returns:
            Sanitized SQL

        Note:
            This is a basic check. Parameter binding is the primary defense against SQL injection.
        """
        # Remove SQL comments (-- and /* */)
        # Only strip obvious comment patterns, don't break legitimate SQL
        import re

        # This is just basic sanitization - the real protection is parameterized queries
        # We don't want to be too aggressive here as it might break valid SQL

        # Check for suspicious patterns (but don't block valid SQL)
        suspicious_patterns = [
            r';.*DROP\s+TABLE',
            r';.*DELETE\s+FROM',
            r';.*INSERT\s+INTO',
            r'UNION.*SELECT',
        ]

        sql_upper = sql.upper()
        for pattern in suspicious_patterns:
            if re.search(pattern, sql_upper):
                raise QueryValidationError(
                    f"SQL contains suspicious pattern. Use parameters instead of string concatenation."
                )

        return sql
