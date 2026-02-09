"""
Gunicorn configuration for Quantum Chat.

Applies runtime patches needed for the chat application:
- Fixes condition evaluation for comparison expressions
- Fixes databinding for missing scoped variables
- Fixes q:set execution inside q:if bodies
- Fixes array operation databinding resolution
- Fixes update_variable scope prefix handling
"""

import os
import sys
from pathlib import Path

# Ensure sys.path matches what wsgi.py sets up
# wsgi.py inserts /app/src so modules are loaded as runtime.* not src.runtime.*
_src_dir = str(Path(__file__).parent / 'src')
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# Single worker for shared in-memory application scope
workers = int(os.environ.get('GUNICORN_WORKERS', 1))
bind = '0.0.0.0:8080'
timeout = 120
accesslog = '-'
errorlog = '-'
loglevel = 'info'


def post_worker_init(worker):
    """Apply runtime patches after worker initialization."""
    _patch_execution_context()
    _patch_component_runtime()
    _patch_web_server_secret_key()
    print("[PATCH] Quantum runtime patches applied", flush=True)


def _patch_execution_context():
    """Fix update_variable to handle scope prefixes."""
    from runtime.execution_context import ExecutionContext

    original_update = ExecutionContext.update_variable

    def patched_update_variable(self, name, value):
        if '.' in name:
            prefix, var_name = name.split('.', 1)
            if prefix in ['session', 'application', 'request', 'cookie']:
                if prefix == 'session':
                    self.session_vars[var_name] = value
                elif prefix == 'application':
                    self.application_vars[var_name] = value
                elif prefix == 'request':
                    self.request_vars[var_name] = value
                elif prefix == 'cookie':
                    self.session_vars[f'__cookie_{var_name}'] = value
                return
        original_update(self, name, value)

    ExecutionContext.update_variable = patched_update_variable


def _patch_component_runtime():
    """Fix component runtime for chat app needs."""
    from runtime.component import ComponentRuntime

    # --- Patch 1: Fix _execute_body to handle all statement types ---
    def patched_execute_body(self, statements, context):
        for statement in statements:
            from core.ast_nodes import QuantumReturn
            from core.features.conditionals.src.ast_node import IfNode
            if isinstance(statement, QuantumReturn):
                return self._process_return_value(statement.value, context)
            else:
                result = self._execute_statement(statement, self.execution_context)
                if result is not None and isinstance(statement, IfNode):
                    return result
        return None

    ComponentRuntime._execute_body = patched_execute_body

    # --- Patch 2: Fix _evaluate_condition for comparison expressions ---
    def patched_evaluate_condition(self, condition, context):
        if not condition:
            return False
        try:
            comparison_ops = ['==', '!=', '>=', '<=', '>', '<']
            has_comparison = any(op in condition for op in comparison_ops)

            if has_comparison and '{' in condition:
                return _evaluate_comparison(self, condition, context, comparison_ops)

            evaluated_condition = self._apply_databinding(condition, context)

            if not isinstance(evaluated_condition, str):
                return bool(evaluated_condition)

            if '{' in evaluated_condition:
                return False

            try:
                return bool(eval(evaluated_condition))
            except (SyntaxError, NameError, TypeError):
                return bool(evaluated_condition)
        except Exception:
            return False

    ComponentRuntime._evaluate_condition = patched_evaluate_condition

    # --- Patch 3: Fix databinding for missing scoped variables ---
    original_databinding_expr = ComponentRuntime._evaluate_databinding_expression

    def patched_databinding_expression(self, expr, context):
        try:
            return original_databinding_expr(self, expr, context)
        except (ValueError, KeyError):
            if '.' in expr:
                parts = expr.split('.')
                if parts[0] in ('session', 'application', 'request', 'cookie', 'form', 'query'):
                    return ''
            raise

    ComponentRuntime._evaluate_databinding_expression = patched_databinding_expression

    # --- Patch 4: Fix array operations to resolve databinding in values ---
    def patched_array_operation(self, set_node, exec_context):
        from runtime.execution_context import VariableNotFoundError

        try:
            current_value = exec_context.get_variable(set_node.name)
        except VariableNotFoundError:
            current_value = []

        if not isinstance(current_value, list):
            from runtime.component import ComponentExecutionError
            raise ComponentExecutionError(
                f"Cannot perform array operation on non-array: {type(current_value)}")

        result = current_value.copy()

        resolved_value = set_node.value
        if resolved_value and set_node.operation in ("append", "prepend", "remove"):
            dict_context = exec_context.get_all_variables()
            resolved = self._apply_databinding(resolved_value, dict_context)
            if resolved is not None:
                resolved_value = resolved

        if set_node.operation == "append":
            if resolved_value:
                result.append(resolved_value)
        elif set_node.operation == "prepend":
            if resolved_value:
                result.insert(0, resolved_value)
        elif set_node.operation == "remove":
            if resolved_value and resolved_value in result:
                result.remove(resolved_value)
        elif set_node.operation == "removeAt":
            index = int(set_node.value) if set_node.value else 0
            if 0 <= index < len(result):
                result.pop(index)
        elif set_node.operation == "clear":
            result = []
        elif set_node.operation == "sort":
            result.sort()
        elif set_node.operation == "reverse":
            result.reverse()
        elif set_node.operation == "unique":
            seen = []
            for item in result:
                if item not in seen:
                    seen.append(item)
            result = seen

        return result

    ComponentRuntime._execute_set_array_operation = patched_array_operation


def _evaluate_comparison(runtime, condition, context, comparison_ops):
    """Evaluate a condition with {databinding} and comparison operators."""
    op = None
    op_pos = -1
    for candidate in sorted(comparison_ops, key=len, reverse=True):
        pos = condition.find(candidate)
        if pos != -1:
            before = condition[:pos]
            if before.count('{') == before.count('}'):
                op = candidate
                op_pos = pos
                break

    if op is None:
        return False

    left_str = condition[:op_pos].strip()
    right_str = condition[op_pos + len(op):].strip()

    left_val = runtime._apply_databinding(left_str, context) if left_str else ''
    right_val = runtime._apply_databinding(right_str, context) if right_str else ''

    # Strip quotes from literals
    for val_name in ['left_val', 'right_val']:
        val = locals()[val_name]
        if isinstance(val, str):
            val = val.strip()
            if (val.startswith("'") and val.endswith("'")) or \
               (val.startswith('"') and val.endswith('"')):
                val = val[1:-1]
            if val_name == 'left_val':
                left_val = val
            else:
                right_val = val

    if op == '==':
        return left_val == right_val
    elif op == '!=':
        return left_val != right_val
    elif op in ('>', '<', '>=', '<='):
        try:
            left_num = float(left_val) if isinstance(left_val, str) else left_val
            right_num = float(right_val) if isinstance(right_val, str) else right_val
            if op == '>':
                return left_num > right_num
            elif op == '<':
                return left_num < right_num
            elif op == '>=':
                return left_num >= right_num
            elif op == '<=':
                return left_num <= right_num
        except (ValueError, TypeError):
            return str(left_val) > str(right_val) if op == '>' else \
                   str(left_val) < str(right_val) if op == '<' else \
                   str(left_val) >= str(right_val) if op == '>=' else \
                   str(left_val) <= str(right_val)
    return False


def _patch_web_server_secret_key():
    """Ensure web server uses stable secret key from env var."""
    import sys as _sys

    # Access the REAL app that gunicorn is serving
    # Gunicorn loaded it as 'src.runtime.wsgi', not 'runtime.wsgi'
    wsgi_mod = _sys.modules.get('src.runtime.wsgi')
    if wsgi_mod:
        real_app = wsgi_mod.app
        secret = os.environ.get('QUANTUM_SECRET_KEY')
        if secret:
            real_app.secret_key = secret
            print(f"[PATCH] Secret key set from env var", flush=True)
