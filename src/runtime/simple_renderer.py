"""
Simple Component Renderer - Renders AST to HTML

Supports:
- HTML tags with databinding
- q:set (variables)
- q:if/q:else
- q:loop (range and array)
- q:function definitions
- q:call (function invocation)
- q:query (database queries)
- q:action (form handling)
- q:mail (email sending)
- q:file (file uploads)
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ast_nodes import *
from core.parser import QuantumParser
from runtime.databinding import resolve, evaluate, resolve_condition
from core.features.functions.src import FunctionRuntime, register_function


class SimpleRenderer:
    """Renders Quantum components to HTML"""

    def __init__(self,
                 db_service=None,
                 email_service=None,
                 file_service=None,
                 action_handler=None):
        self.parser = QuantumParser()
        self.function_runtime = FunctionRuntime()

        # Lazy-load services (imported when first used)
        self._db_service = db_service
        self._email_service = email_service
        self._file_service = file_service
        self._action_handler = action_handler

    @property
    def db_service(self):
        """Lazy-load database service"""
        if self._db_service is None:
            from runtime.database_service import DatabaseService
            self._db_service = DatabaseService()
        return self._db_service

    @property
    def email_service(self):
        """Lazy-load email service"""
        if self._email_service is None:
            from runtime.email_service import EmailService
            self._email_service = EmailService()
        return self._email_service

    @property
    def file_service(self):
        """Lazy-load file upload service"""
        if self._file_service is None:
            from runtime.file_upload_service import FileUploadService
            self._file_service = FileUploadService()
        return self._file_service

    @property
    def action_handler(self):
        """Lazy-load action handler"""
        if self._action_handler is None:
            from runtime.action_handler import ActionHandler
            self._action_handler = ActionHandler()
        return self._action_handler

    def render_file(self, file_path: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Render component file to HTML

        Args:
            file_path: Path to .q file
            context: Initial context (variables, query params, etc)

        Returns:
            Rendered HTML string
        """
        # Parse file
        ast = self.parser.parse_file(file_path)

        # Initialize context
        if context is None:
            context = {}

        # Render component
        return self.render_component(ast, context)

    def render_component(self, component: ComponentNode, context: Dict[str, Any]) -> str:
        """Render component AST to HTML"""

        # Register functions
        for statement in component.statements:
            if isinstance(statement, FunctionNode):
                self.function_runtime.register_function(statement)

        # Render statements
        html_parts = []
        for statement in component.statements:
            rendered = self.render_statement(statement, context)
            if rendered:
                html_parts.append(rendered)

        return ''.join(html_parts)

    def render_statement(self, statement: QuantumNode, context: Dict[str, Any]) -> str:
        """Render single statement"""

        statement_type = type(statement).__name__

        # HTML elements
        if isinstance(statement, HTMLNode):
            return self.render_html_node(statement, context)

        # Text nodes
        if isinstance(statement, TextNode):
            return self.render_text_node(statement, context)

        # q:set
        if isinstance(statement, SetNode):
            self.execute_set(statement, context)
            return ""

        # q:if
        if isinstance(statement, IfNode):
            return self.render_if(statement, context)

        # q:loop
        if isinstance(statement, LoopNode):
            return self.render_loop(statement, context)

        # q:call
        if isinstance(statement, FunctionCallNode):
            return self.execute_function_call(statement, context)

        # q:query - NEW!
        if isinstance(statement, QueryNode):
            self.execute_query(statement, context)
            return ""

        # q:action - NEW!
        if isinstance(statement, ActionNode):
            return self.execute_action(statement, context)

        # q:mail - NEW!
        if isinstance(statement, MailNode):
            self.execute_mail(statement, context)
            return ""

        # q:file - NEW!
        if isinstance(statement, FileNode):
            self.execute_file(statement, context)
            return ""

        # q:function (definition, no output)
        if isinstance(statement, FunctionNode):
            return ""

        # Unknown statement
        return f"<!-- Unknown statement: {statement_type} -->"

    def render_html_node(self, node: HTMLNode, context: Dict[str, Any]) -> str:
        """Render HTML element"""

        # Resolve tag name
        tag = node.tag

        # Build attributes
        attrs = []
        if node.attributes:
            for key, value in node.attributes.items():
                # Resolve databinding in attribute values
                resolved_value = resolve(value, context)
                attrs.append(f'{key}="{resolved_value}"')

        attrs_str = ' ' + ' '.join(attrs) if attrs else ''

        # Self-closing tags
        if tag in HTML_VOID_ELEMENTS:
            return f'<{tag}{attrs_str} />'

        # Render children
        children_html = []
        if node.children:
            for child in node.children:
                child_html = self.render_statement(child, context)
                if child_html:
                    children_html.append(child_html)

        children_str = ''.join(children_html)

        return f'<{tag}{attrs_str}>{children_str}</{tag}>'

    def render_text_node(self, node: TextNode, context: Dict[str, Any]) -> str:
        """Render text with databinding"""
        if not node.content:
            return ""

        # Resolve databinding expressions
        return resolve(node.content, context)

    def execute_set(self, node: SetNode, context: Dict[str, Any]):
        """Execute q:set - Set variable in context"""

        value = node.value

        # Resolve databinding in value
        if value:
            # Check if it's a databinding expression or literal
            if '{' in value and '}' in value:
                # Has databinding, resolve it first (handles {expr} -> result)
                resolved_str = resolve(value, context)
                # Then parse the result as a literal
                resolved_value = self._parse_literal(resolved_str)
            else:
                # Literal value - try to parse as number or use as string
                resolved_value = self._parse_literal(value)
        else:
            resolved_value = node.default

        # Handle operations
        if node.operation == 'assign':
            context[node.name] = resolved_value
        elif node.operation == 'add':
            current = context.get(node.name, 0)
            context[node.name] = current + self._to_number(resolved_value)
        elif node.operation == 'subtract':
            current = context.get(node.name, 0)
            context[node.name] = current - self._to_number(resolved_value)
        elif node.operation == 'multiply':
            current = context.get(node.name, 1)
            context[node.name] = current * self._to_number(resolved_value)
        elif node.operation == 'divide':
            current = context.get(node.name, 1)
            context[node.name] = current / self._to_number(resolved_value)

    def render_if(self, node: IfNode, context: Dict[str, Any]) -> str:
        """Render q:if conditional"""

        # Evaluate condition
        condition_result = resolve_condition(node.condition, context)

        if condition_result:
            # Render if body
            html_parts = []
            for statement in node.body:
                rendered = self.render_statement(statement, context)
                if rendered:
                    html_parts.append(rendered)
            return ''.join(html_parts)
        else:
            # Check elseif
            if node.elseif_nodes:
                for elseif_node in node.elseif_nodes:
                    elseif_result = resolve_condition(elseif_node.condition, context)
                    if elseif_result:
                        html_parts = []
                        for statement in elseif_node.body:
                            rendered = self.render_statement(statement, context)
                            if rendered:
                                html_parts.append(rendered)
                        return ''.join(html_parts)

            # Render else body
            if node.else_body:
                html_parts = []
                for statement in node.else_body:
                    rendered = self.render_statement(statement, context)
                    if rendered:
                        html_parts.append(rendered)
                return ''.join(html_parts)

        return ""

    def render_loop(self, node: LoopNode, context: Dict[str, Any]) -> str:
        """Render q:loop"""

        html_parts = []

        if node.loop_type == 'range':
            # Range loop: from..to
            # Evaluate from/to values (might contain {variable})
            from_str = str(node.from_value) if node.from_value else "0"
            to_str = str(node.to_value) if node.to_value else "0"

            # Resolve any databinding in from/to
            if '{' in from_str:
                resolved_from = resolve(from_str, context)
                start_val = self._parse_literal(resolved_from)
            else:
                start_val = self._parse_literal(from_str)

            if '{' in to_str:
                resolved_to = resolve(to_str, context)
                end_val = self._parse_literal(resolved_to)
            else:
                end_val = self._parse_literal(to_str)

            start = int(start_val) if start_val is not None else 0
            end = int(end_val) if end_val is not None else 0
            step = int(node.step_value) if node.step_value else 1

            for i in range(start, end + 1, step):
                # Create loop context
                loop_context = context.copy()
                loop_context[node.var_name] = i

                # Render body
                for statement in node.body:
                    rendered = self.render_statement(statement, loop_context)
                    if rendered:
                        html_parts.append(rendered)

        elif node.loop_type == 'array':
            # Array loop - iterate over actual data
            # node.items can be:
            # - Variable name: "users"
            # - Expression: "{query.users.data}"

            if node.items:
                # Resolve the array expression
                items_value = resolve(node.items, context) if '{' in str(node.items) else context.get(node.items, [])

                # If it's still a string, try to get from context
                if isinstance(items_value, str):
                    items_value = context.get(items_value, [])

                # Handle QueryResult objects (from q:query)
                if hasattr(items_value, 'data'):
                    items_value = items_value.data

                # Ensure it's iterable
                if not isinstance(items_value, (list, tuple)):
                    items_value = []

                # Iterate over items
                for index, item in enumerate(items_value):
                    # Create loop context
                    loop_context = context.copy()
                    loop_context[node.var_name] = item
                    loop_context[f'{node.var_name}_index'] = index
                    loop_context[f'{node.var_name}_count'] = index + 1

                    # Render body
                    for statement in node.body:
                        rendered = self.render_statement(statement, loop_context)
                        if rendered:
                            html_parts.append(rendered)

        return ''.join(html_parts)

    def execute_function_call(self, node: FunctionCallNode, context: Dict[str, Any]) -> str:
        """Execute q:call - Call function and optionally store result"""

        # Resolve arguments
        resolved_args = {}
        for key, value in node.args.items():
            resolved_args[key] = evaluate(value, context)

        # Call function
        try:
            result = self.function_runtime.call(node.function_name, resolved_args, context)

            # Store result if specified
            if node.result_var:
                context[node.result_var] = result
                return ""  # No output if storing result
            else:
                # Return result as string
                return str(result) if result is not None else ""

        except Exception as e:
            return f"<!-- Function call error: {e} -->"

    def execute_query(self, node: QueryNode, context: Dict[str, Any]) -> None:
        """Execute q:query - Database query execution"""
        try:
            # Resolve SQL with databinding
            sql = resolve(node.sql, context) if node.sql else ""

            # Execute query through database service
            result = self.db_service.execute_query(
                sql=sql,
                datasource=node.datasource or "default",
                params=context,
                max_rows=node.max_rows,
                timeout=node.timeout
            )

            # Store result in context
            context[node.name] = result

        except Exception as e:
            # Store error in context for debugging
            context[node.name] = {
                'success': False,
                'error': str(e),
                'data': [],
                'record_count': 0
            }
            print(f"Query error: {e}")

    def execute_action(self, node: ActionNode, context: Dict[str, Any]) -> str:
        """Execute q:action - Form/POST request handling"""
        try:
            # Check if this action should execute (based on HTTP method)
            from flask import request

            # Get action name from URL query param
            action_name = request.args.get('action', '')

            # Only execute if action name matches and method matches
            if action_name == node.name and request.method == node.method:
                # Handle action through action handler
                redirect_url, status_code = self.action_handler.handle_action(node, context)

                # If redirect, return special marker
                if redirect_url:
                    context['__redirect__'] = redirect_url
                    context['__redirect_status__'] = status_code
                    return f"<!-- Redirecting to {redirect_url} -->"

            return ""

        except Exception as e:
            return f"<!-- Action error: {e} -->"

    def execute_mail(self, node: MailNode, context: Dict[str, Any]) -> None:
        """Execute q:mail - Send email"""
        try:
            # Resolve email fields with databinding
            to = resolve(node.to, context) if node.to else ""
            subject = resolve(node.subject, context) if node.subject else ""
            from_addr = resolve(node.from_addr, context) if node.from_addr else None

            # Get body content (render child nodes)
            body_parts = []
            for statement in node.body:
                rendered = self.render_statement(statement, context)
                if rendered:
                    body_parts.append(rendered)
            body = ''.join(body_parts)

            # Send email
            result = self.email_service.send_email(
                to=to,
                subject=subject,
                body=body,
                from_addr=from_addr,
                cc=node.cc,
                bcc=node.bcc,
                reply_to=node.reply_to,
                email_type=node.type or "html"
            )

            # Store result in context if name provided
            if hasattr(node, 'result_var') and node.result_var:
                context[node.result_var] = result

        except Exception as e:
            print(f"Mail error: {e}")
            if hasattr(node, 'result_var') and node.result_var:
                context[node.result_var] = {'success': False, 'error': str(e)}

    def execute_file(self, node: FileNode, context: Dict[str, Any]) -> None:
        """Execute q:file - Handle file upload"""
        try:
            from flask import request

            # Get file from request
            file_field = node.field or 'file'
            uploaded_file = request.files.get(file_field)

            if uploaded_file and uploaded_file.filename:
                # Parse size limit
                max_size = None
                if node.max_size:
                    max_size = self.file_service.parse_size(node.max_size)

                # Handle upload
                result = self.file_service.handle_upload(
                    file=uploaded_file,
                    destination=node.destination or "uploads",
                    allowed_extensions=node.accept.split(',') if node.accept else None,
                    max_file_size=max_size,
                    name_conflict=node.name_conflict or "makeunique"
                )

                # Store result in context
                context[node.result_var or 'uploadedFile'] = result
            else:
                context[node.result_var or 'uploadedFile'] = {
                    'success': False,
                    'error': 'No file uploaded'
                }

        except Exception as e:
            print(f"File upload error: {e}")
            context[node.result_var or 'uploadedFile'] = {
                'success': False,
                'error': str(e)
            }

    def _to_number(self, value: Any) -> float:
        """Convert value to number"""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 0.0
        return 0.0

    def _parse_literal(self, value: str) -> Any:
        """Parse literal value (string, number, boolean, etc)"""
        value = value.strip()

        # Boolean
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False

        # Null/None
        if value.lower() in ('null', 'none'):
            return None

        # Number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # String (return as is)
        return value


# Helper function
def render(file_path: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Render component file to HTML"""
    renderer = SimpleRenderer()
    return renderer.render_file(file_path, context)
