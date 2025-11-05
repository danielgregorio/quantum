"""
Quantum Action Handler - Process server-side actions from forms

Phase A: Forms & Actions
Handles POST/PUT/DELETE requests, validates parameters, executes action body,
manages flash messages, and performs redirects.
"""

from typing import Dict, Any, Optional, List, Tuple
from flask import request, session, redirect as flask_redirect
from core.ast_nodes import (
    ActionNode, RedirectNode, FlashNode, QuantumParam,
    QueryNode, SetNode, IfNode
)
from runtime.execution_context import ExecutionContext
from runtime.component import ComponentRuntime
import re


class ValidationError(Exception):
    """Parameter validation error"""
    pass


class ActionHandler:
    """
    Handles server-side action execution.

    Workflow:
    1. Extract form data from request
    2. Validate against q:param definitions
    3. Execute action body statements
    4. Handle flash messages
    5. Perform redirect
    """

    def __init__(self, component_runtime: Optional[ComponentRuntime] = None):
        self.component_runtime = component_runtime or ComponentRuntime()

    def handle_action(
        self,
        action: ActionNode,
        context: Optional[ExecutionContext] = None
    ) -> Tuple[Optional[str], int]:
        """
        Handle action execution.

        Returns:
            Tuple[redirect_url, status_code] or None if no redirect
        """

        # Use provided context or create new one
        if context is None:
            context = ExecutionContext()

        try:
            # 1. Extract form data
            form_data = self._extract_form_data()

            # 2. Validate parameters
            validated_params = self._validate_parameters(action.params, form_data)

            # 3. Add validated params to context
            for key, value in validated_params.items():
                context.set_variable(key, value)

            # 4. Execute action body
            redirect_info = self._execute_action_body(action, context)

            # 5. Return redirect if present
            if redirect_info:
                return redirect_info

            return None, 200

        except ValidationError as e:
            # Validation failed - set error flash and redirect back
            self._set_flash_message(str(e), 'error')
            # Redirect to referer or home
            referer = request.referrer or '/'
            return referer, 302

        except Exception as e:
            # Unexpected error
            self._set_flash_message(f'Action error: {str(e)}', 'error')
            return request.referrer or '/', 500

    def _extract_form_data(self) -> Dict[str, Any]:
        """Extract data from POST/PUT/DELETE request"""

        if request.method in ['POST', 'PUT', 'PATCH']:
            # Form data or JSON
            if request.is_json:
                return request.get_json() or {}
            else:
                return request.form.to_dict()

        elif request.method == 'DELETE':
            # DELETE might have JSON body
            if request.is_json:
                return request.get_json() or {}
            return {}

        return {}

    def _validate_parameters(
        self,
        params: List[QuantumParam],
        form_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate form data against q:param definitions.

        Raises ValidationError if validation fails.
        """

        validated = {}

        for param in params:
            value = form_data.get(param.name)

            # Check required
            if param.required and (value is None or value == ''):
                raise ValidationError(f"Parameter '{param.name}' is required")

            # Skip validation if optional and not provided
            if value is None or value == '':
                if param.default is not None:
                    validated[param.name] = param.default
                continue

            # Type validation and conversion
            validated_value = self._validate_type(param, value)

            # Additional validation rules
            self._validate_rules(param, validated_value)

            validated[param.name] = validated_value

        return validated

    def _validate_type(self, param: QuantumParam, value: Any) -> Any:
        """Validate and convert parameter type"""

        if param.type == 'string':
            return str(value)

        elif param.type == 'email':
            email_str = str(value)
            # Simple email validation
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email_str):
                raise ValidationError(f"Parameter '{param.name}' must be a valid email")
            return email_str

        elif param.type == 'url':
            url_str = str(value)
            if not re.match(r'^https?://', url_str):
                raise ValidationError(f"Parameter '{param.name}' must be a valid URL")
            return url_str

        elif param.type == 'integer':
            try:
                return int(value)
            except (ValueError, TypeError):
                raise ValidationError(f"Parameter '{param.name}' must be an integer")

        elif param.type == 'decimal' or param.type == 'float':
            try:
                return float(value)
            except (ValueError, TypeError):
                raise ValidationError(f"Parameter '{param.name}' must be a number")

        elif param.type == 'boolean':
            # Handle various boolean representations
            if isinstance(value, bool):
                return value
            str_value = str(value).lower()
            if str_value in ['true', '1', 'yes', 'on']:
                return True
            elif str_value in ['false', '0', 'no', 'off', '']:
                return False
            else:
                raise ValidationError(f"Parameter '{param.name}' must be true or false")

        # Default: return as string
        return str(value)

    def _validate_rules(self, param: QuantumParam, value: Any):
        """Validate additional rules (min, max, length, etc.)"""

        # String length validation
        if param.type == 'string' and isinstance(value, str):
            if param.minlength and len(value) < param.minlength:
                raise ValidationError(
                    f"Parameter '{param.name}' must be at least {param.minlength} characters"
                )
            if param.maxlength and len(value) > param.maxlength:
                raise ValidationError(
                    f"Parameter '{param.name}' must be at most {param.maxlength} characters"
                )

        # Numeric range validation
        if param.type in ['integer', 'decimal', 'float'] and isinstance(value, (int, float)):
            if param.min is not None and value < param.min:
                raise ValidationError(
                    f"Parameter '{param.name}' must be at least {param.min}"
                )
            if param.max is not None and value > param.max:
                raise ValidationError(
                    f"Parameter '{param.name}' must be at most {param.max}"
                )

        # Enum validation
        if param.enum:
            allowed_values = [v.strip() for v in param.enum.split(',')]
            if str(value) not in allowed_values:
                raise ValidationError(
                    f"Parameter '{param.name}' must be one of: {', '.join(allowed_values)}"
                )

        # Pattern validation
        if param.pattern and isinstance(value, str):
            if not re.match(param.pattern, value):
                raise ValidationError(
                    f"Parameter '{param.name}' does not match required pattern"
                )

    def _execute_action_body(
        self,
        action: ActionNode,
        context: ExecutionContext
    ) -> Optional[Tuple[str, int]]:
        """
        Execute action body statements.

        Returns redirect info if redirect encountered, None otherwise.
        """

        for statement in action.body:
            # Handle redirect
            if isinstance(statement, RedirectNode):
                url = self._resolve_databinding(statement.url, context)

                # Set flash message if present
                if statement.flash:
                    flash_msg = self._resolve_databinding(statement.flash, context)
                    self._set_flash_message(flash_msg, 'success')

                return url, statement.status

            # Handle flash
            elif isinstance(statement, FlashNode):
                message = self._resolve_databinding(statement.message, context)
                self._set_flash_message(message, statement.flash_type)

            # Handle set
            elif isinstance(statement, SetNode):
                # Execute set to update context
                value = context.resolve_expression(statement.value)
                context.set_variable(statement.name, value)

            # Handle query (would need DatabaseRuntime)
            elif isinstance(statement, QueryNode):
                # TODO: Execute query when database runtime is implemented
                pass

            # Handle if (conditional redirect/flash)
            elif isinstance(statement, IfNode):
                # Evaluate condition
                condition_result = context.evaluate_condition(statement.condition)

                if condition_result:
                    # Execute if body
                    for if_stmt in statement.if_body:
                        result = self._execute_single_statement(if_stmt, context)
                        if result:  # Redirect found
                            return result
                else:
                    # Try elseif blocks
                    for elseif_condition, elseif_body in statement.elseif_blocks:
                        if context.evaluate_condition(elseif_condition):
                            for elseif_stmt in elseif_body:
                                result = self._execute_single_statement(elseif_stmt, context)
                                if result:
                                    return result
                            break
                    else:
                        # Execute else body
                        for else_stmt in statement.else_body:
                            result = self._execute_single_statement(else_stmt, context)
                            if result:
                                return result

        return None

    def _execute_single_statement(
        self,
        statement,
        context: ExecutionContext
    ) -> Optional[Tuple[str, int]]:
        """Execute a single statement and return redirect if encountered"""

        if isinstance(statement, RedirectNode):
            url = self._resolve_databinding(statement.url, context)
            if statement.flash:
                flash_msg = self._resolve_databinding(statement.flash, context)
                self._set_flash_message(flash_msg, 'success')
            return url, statement.status

        elif isinstance(statement, FlashNode):
            message = self._resolve_databinding(statement.message, context)
            self._set_flash_message(message, statement.flash_type)

        elif isinstance(statement, SetNode):
            value = context.resolve_expression(statement.value)
            context.set_variable(statement.name, value)

        return None

    def _resolve_databinding(self, text: str, context: ExecutionContext) -> str:
        """Resolve {variable} databinding in text"""
        if not text or '{' not in text:
            return text

        import re

        def replace_var(match):
            var_name = match.group(1)
            value = context.get_variable(var_name)
            return str(value) if value is not None else ''

        return re.sub(r'\{([^}]+)\}', replace_var, text)

    def _set_flash_message(self, message: str, flash_type: str = 'info'):
        """Set flash message in session"""
        if 'flash' not in session:
            session['flash'] = {}

        session['flash'] = {
            'message': message,
            'type': flash_type
        }
        session.modified = True

    def get_flash_message(self) -> Optional[Dict[str, str]]:
        """Get and clear flash message from session"""
        if 'flash' in session:
            flash = session.pop('flash')
            session.modified = True
            return flash
        return None
