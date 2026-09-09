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
    # _patch_component_runtime() removed — see the note below.
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


# NOTE: this file used to define _patch_component_runtime() and call it from
# the worker hook above. It monkeypatched ComponentRuntime to work around
# framework bugs of the time — missing scoped variables resolving badly, text
# nodes dropped inside q:loop, non-string values reaching html.escape().
#
# All of those are fixed upstream now. The patch was removed because one of its
# three parts re-implemented the old _evaluate_condition, which interpolates
# variable VALUES into the condition string and then calls a bare eval() on the
# result — the exact pattern PUBLIC_RELEASE_PLAN.md P0.1 exists to eliminate.
# It was already inert (it imports `runtime.component`, a layout that stopped
# existing when src/ became the quantum/ package), so this removes dead code
# rather than changing behaviour.

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
