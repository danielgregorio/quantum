"""
Quantum Built-in Validators - Validation rules for q:set
"""

import re
from typing import Any, Optional, Tuple


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


class QuantumValidators:
    """Built-in validators for common data types"""

    # Regex patterns for built-in validators
    PATTERNS = {
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'url': r'^https?://[^\s/$.?#].[^\s]*$',
        'cpf': r'^\d{3}\.\d{3}\.\d{3}-\d{2}$',
        'cnpj': r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$',
        'phone': r'^\(\d{2}\)\s?\d{4,5}-\d{4}$',
        'cep': r'^\d{5}-\d{3}$',
        'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        'creditcard': r'^\d{4}\s?\d{4}\s?\d{4}\s?\d{4}$',
        'ipv4': r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$',
        'ipv6': r'^([0-9a-fA-F]{0,4}:){7}[0-9a-fA-F]{0,4}$',
    }

    @staticmethod
    def validate(value: Any, rule: str, **kwargs) -> Tuple[bool, Optional[str]]:
        """
        Validate a value against a rule

        Args:
            value: Value to validate
            rule: Validation rule name or regex pattern
            **kwargs: Additional validation parameters

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if value is None:
            return True, None  # None is valid unless required=True

        # Convert to string for pattern matching
        value_str = str(value)

        # Check if it's a built-in validator
        if rule in QuantumValidators.PATTERNS:
            pattern = QuantumValidators.PATTERNS[rule]
            if re.match(pattern, value_str):
                return True, None
            else:
                return False, f"Invalid {rule} format"

        # Check if it's a custom regex pattern
        if rule.startswith('^') or rule.startswith('.*'):
            try:
                if re.match(rule, value_str):
                    return True, None
                else:
                    return False, f"Value does not match pattern: {rule}"
            except re.error as e:
                return False, f"Invalid regex pattern: {e}"

        # Unknown validator
        return False, f"Unknown validator: {rule}"

    @staticmethod
    def validate_cpf(cpf: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Brazilian CPF (with digit verification)

        Args:
            cpf: CPF string (xxx.xxx.xxx-xx)

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Remove formatting
        cpf_digits = re.sub(r'\D', '', cpf)

        # Check length
        if len(cpf_digits) != 11:
            return False, "CPF must have 11 digits"

        # Check for known invalid CPFs (all same digit)
        if cpf_digits == cpf_digits[0] * 11:
            return False, "Invalid CPF"

        # Validate first check digit
        sum_digits = sum(int(cpf_digits[i]) * (10 - i) for i in range(9))
        check_digit_1 = (sum_digits * 10 % 11) % 10

        if int(cpf_digits[9]) != check_digit_1:
            return False, "Invalid CPF check digit"

        # Validate second check digit
        sum_digits = sum(int(cpf_digits[i]) * (11 - i) for i in range(10))
        check_digit_2 = (sum_digits * 10 % 11) % 10

        if int(cpf_digits[10]) != check_digit_2:
            return False, "Invalid CPF check digit"

        return True, None

    @staticmethod
    def validate_cnpj(cnpj: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Brazilian CNPJ (with digit verification)

        Args:
            cnpj: CNPJ string (xx.xxx.xxx/xxxx-xx)

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Remove formatting
        cnpj_digits = re.sub(r'\D', '', cnpj)

        # Check length
        if len(cnpj_digits) != 14:
            return False, "CNPJ must have 14 digits"

        # Check for known invalid CNPJs (all same digit)
        if cnpj_digits == cnpj_digits[0] * 14:
            return False, "Invalid CNPJ"

        # Validate first check digit
        weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        sum_digits = sum(int(cnpj_digits[i]) * weights_1[i] for i in range(12))
        check_digit_1 = (sum_digits % 11)
        check_digit_1 = 0 if check_digit_1 < 2 else 11 - check_digit_1

        if int(cnpj_digits[12]) != check_digit_1:
            return False, "Invalid CNPJ check digit"

        # Validate second check digit
        weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        sum_digits = sum(int(cnpj_digits[i]) * weights_2[i] for i in range(13))
        check_digit_2 = (sum_digits % 11)
        check_digit_2 = 0 if check_digit_2 < 2 else 11 - check_digit_2

        if int(cnpj_digits[13]) != check_digit_2:
            return False, "Invalid CNPJ check digit"

        return True, None

    @staticmethod
    def validate_required(value: Any) -> Tuple[bool, Optional[str]]:
        """Check if value is not None/empty"""
        if value is None:
            return False, "This field is required"
        if isinstance(value, str) and value.strip() == "":
            return False, "This field cannot be empty"
        if isinstance(value, (list, dict)) and len(value) == 0:
            return False, "This field cannot be empty"
        return True, None

    @staticmethod
    def validate_range(value: Any, range_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validate value is within range

        Args:
            value: Value to check
            range_str: Range string like "0..100" or "2024-01-01..2025-12-31"

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if '..' not in range_str:
            return False, "Invalid range format (use min..max)"

        parts = range_str.split('..')
        if len(parts) != 2:
            return False, "Invalid range format (use min..max)"

        min_val, max_val = parts

        # Try numeric comparison
        try:
            num_value = float(value)
            num_min = float(min_val)
            num_max = float(max_val)

            if num_min <= num_value <= num_max:
                return True, None
            else:
                return False, f"Value must be between {min_val} and {max_val}"
        except (ValueError, TypeError):
            pass

        # Try string comparison (for dates, etc.)
        value_str = str(value)
        if min_val <= value_str <= max_val:
            return True, None
        else:
            return False, f"Value must be between {min_val} and {max_val}"

    @staticmethod
    def validate_enum(value: Any, enum_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validate value is in enum list

        Args:
            value: Value to check
            enum_str: Comma-separated list like "pending,active,inactive"

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        allowed_values = [v.strip() for v in enum_str.split(',')]
        value_str = str(value)

        if value_str in allowed_values:
            return True, None
        else:
            return False, f"Value must be one of: {', '.join(allowed_values)}"

    @staticmethod
    def validate_min_max(value: Any, min_val: Optional[Any] = None, max_val: Optional[Any] = None) -> Tuple[bool, Optional[str]]:
        """Validate min/max constraints"""
        try:
            num_value = float(value)

            if min_val is not None:
                num_min = float(min_val)
                if num_value < num_min:
                    return False, f"Value must be at least {min_val}"

            if max_val is not None:
                num_max = float(max_val)
                if num_value > num_max:
                    return False, f"Value must be at most {max_val}"

            return True, None

        except (ValueError, TypeError):
            return False, "Value must be numeric for min/max validation"

    @staticmethod
    def validate_length(value: str, minlength: Optional[int] = None, maxlength: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """Validate string length constraints"""
        value_str = str(value)
        length = len(value_str)

        if minlength is not None and length < minlength:
            return False, f"Value must be at least {minlength} characters"

        if maxlength is not None and length > maxlength:
            return False, f"Value must be at most {maxlength} characters"

        return True, None
