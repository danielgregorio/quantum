"""
Gunicorn configuration for Quantum Dashboard.

- Creates SQLite database with tasks table on startup
- Seeds initial demo data
- Applies same runtime patches as chat app
"""

import os
import sys
import sqlite3
from pathlib import Path

# Ensure sys.path matches what wsgi.py sets up
_src_dir = str(Path(__file__).parent / 'src')
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# Single worker for shared state
workers = int(os.environ.get('GUNICORN_WORKERS', 1))
bind = '0.0.0.0:8080'
timeout = 120
accesslog = '-'
errorlog = '-'
loglevel = 'info'


def post_worker_init(worker):
    """Apply runtime patches and initialize database after worker starts."""
    _init_database()
    _patch_execution_context()
    # _patch_component_runtime() removed — see the note below.
    _patch_database_service()
    _patch_renderer()
    _patch_web_server_secret_key()
    print("[PATCH] Quantum Dashboard runtime patches applied", flush=True)


def _init_database():
    """Create SQLite database and seed initial data."""
    db_dir = Path('/app/data')
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / 'tasks.db'

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed data only if table is empty
    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]
    if count == 0:
        seed_tasks = [
            ('Setup project structure', 'Create directories and config files', 'done', 'high'),
            ('Design database schema', 'Define tables for the application', 'done', 'high'),
            ('Implement user authentication', 'Add login/logout with session management', 'pending', 'high'),
            ('Build dashboard UI', 'Create main dashboard with stats and task list', 'pending', 'medium'),
            ('Add API endpoints', 'REST API for CRUD operations', 'pending', 'medium'),
            ('Write unit tests', 'Test coverage for core modules', 'pending', 'low'),
            ('Deploy to production', 'Setup CI/CD and deploy', 'pending', 'low'),
        ]
        cursor.executemany(
            "INSERT INTO tasks (title, description, status, priority) VALUES (?, ?, ?, ?)",
            seed_tasks
        )
        print(f"[DB] Seeded {len(seed_tasks)} tasks", flush=True)

    conn.commit()
    conn.close()
    print(f"[DB] Database initialized at {db_path}", flush=True)


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


def _patch_database_service():
    """Patch DatabaseService to always have local datasources from config."""
    import yaml
    from runtime.database_service import DatabaseService

    # Load datasources from quantum.config.yaml
    config_path = Path('/app/quantum.config.yaml')
    if not config_path.exists():
        config_path = Path('quantum.config.yaml')

    local_ds = {}
    if config_path.exists():
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
        local_ds = cfg.get('datasources', {})

    if not local_ds:
        print("[PATCH] No datasources found in config", flush=True)
        return

    # Monkey-patch DatabaseService.__init__ to inject local_datasources
    # Compatible with both old (no local_datasources param) and new versions
    original_init = DatabaseService.__init__

    def patched_init(self, admin_api_url="http://localhost:8000", **kwargs):
        original_init(self, admin_api_url=admin_api_url)
        # Force-set local_datasources regardless of __init__ signature
        if not hasattr(self, 'local_datasources') or not self.local_datasources:
            self.local_datasources = {}
        self.local_datasources.update(local_ds)

    DatabaseService.__init__ = patched_init

    # Also patch get_datasource_config to check local_datasources first
    original_get_config = DatabaseService.get_datasource_config

    def patched_get_config(self, datasource_name):
        if hasattr(self, 'local_datasources') and datasource_name in self.local_datasources:
            local_cfg = self.local_datasources[datasource_name]
            return {
                'name': datasource_name,
                'type': local_cfg.get('driver', local_cfg.get('type', 'sqlite')),
                'database': local_cfg.get('database', ''),
                'database_name': local_cfg.get('database', local_cfg.get('database_name', '')),
                'host': local_cfg.get('host', 'localhost'),
                'port': local_cfg.get('port', 5432),
                'username': local_cfg.get('username', ''),
                'password': local_cfg.get('password', ''),
            }
        return original_get_config(self, datasource_name)

    DatabaseService.get_datasource_config = patched_get_config
    print(f"[PATCH] DatabaseService patched with datasources: {list(local_ds.keys())}", flush=True)


def _patch_renderer():
    """Fix renderer to handle query loops and non-string attribute values."""
    from runtime.renderer import HTMLRenderer
    from core.ast_nodes import QueryNode
    from core.features.conditionals.src.ast_node import IfNode
    from core.features.loops.src.ast_node import LoopNode
    from core.features.state_management.src.ast_node import SetNode
    import html as html_module

    # Patch render() dispatch to properly route LoopNode and IfNode
    original_render = HTMLRenderer.render

    def patched_render(self, node):
        if isinstance(node, LoopNode):
            return self._render_loop(node)
        elif isinstance(node, IfNode):
            return self._render_if(node)
        elif isinstance(node, (SetNode, QueryNode)):
            return ''
        return original_render(self, node)

    HTMLRenderer.render = patched_render

    # Patch _get_loop_items to handle query loop type
    original_get_loop_items = HTMLRenderer._get_loop_items

    def patched_get_loop_items(self, node):
        if node.loop_type == 'query':
            # Query loop - resolve items from query result variable
            items_expr = node.items
            if not items_expr:
                # Shorthand syntax: query_name is in var_name
                query_name = getattr(node, 'query_name', node.var_name)
                try:
                    data = self.context.get_variable(query_name)
                    if isinstance(data, list):
                        return data
                except Exception:
                    pass
                return []
            # Traditional syntax: items="{tasks}"
            if '{' in items_expr and '}' in items_expr:
                resolved = self._apply_databinding(items_expr)
                if isinstance(resolved, list):
                    return resolved
            return []
        return original_get_loop_items(self, node)

    HTMLRenderer._get_loop_items = patched_get_loop_items

    # Patch _render_loop to set dotted variables for query rows
    original_render_loop = HTMLRenderer._render_loop

    def patched_render_loop(self, node):
        result = []
        items = self._get_loop_items(node)
        if not items:
            return ''
        original_vars = self.context.local_vars.copy()
        try:
            for index, item in enumerate(items):
                self.context.set_variable(node.var_name, item, scope="local")
                # For query loops, set dotted variables (e.g. tasks.title)
                if node.loop_type == 'query' and isinstance(item, dict):
                    for field_name, field_value in item.items():
                        dotted_key = f"{node.var_name}.{field_name}"
                        self.context.set_variable(dotted_key, field_value, scope="local")
                if node.index_name:
                    self.context.set_variable(node.index_name, index, scope="local")
                for child in node.body:
                    result.append(self.render(child))
        finally:
            self.context.local_vars = original_vars
        return ''.join(result)

    HTMLRenderer._render_loop = patched_render_loop

    # Patch _render_html_node to handle non-string attribute values
    original_render_html = HTMLRenderer._render_html_node

    def patched_render_html_node(self, node):
        # Build opening tag with str() safety for attribute values
        tag_parts = [f'<{node.tag}']
        if node.attributes:
            for key, value in node.attributes.items():
                processed_value = self._apply_databinding(value)
                escaped_value = html_module.escape(str(processed_value), quote=True)
                tag_parts.append(f'{key}="{escaped_value}"')
        opening_tag = ' '.join(tag_parts)
        if node.self_closing:
            return opening_tag + ' />'
        opening_tag += '>'
        children_html = self.render_all(node.children) if node.children else ''
        text_content = ''
        if hasattr(node, 'text_content') and node.text_content:
            text_content = self._apply_databinding(node.text_content)
            if not isinstance(text_content, str):
                text_content = str(text_content)
        closing_tag = f'</{node.tag}>'
        return f'{opening_tag}{text_content}{children_html}{closing_tag}'

    HTMLRenderer._render_html_node = patched_render_html_node

    # Patch _evaluate_condition for proper comparison with databinding
    def patched_renderer_evaluate_condition(self, condition):
        if not condition:
            return False
        try:
            comparison_ops = ['==', '!=', '>=', '<=', '>', '<']
            has_comparison = any(op in condition for op in comparison_ops)

            if has_comparison and '{' in condition:
                # Find the operator, splitting around databinding expressions
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

                if op:
                    left_str = condition[:op_pos].strip()
                    right_str = condition[op_pos + len(op):].strip()

                    left_val = self._apply_databinding(left_str) if left_str else ''
                    right_val = self._apply_databinding(right_str) if right_str else ''

                    # Convert to string for comparison
                    left_val = str(left_val).strip() if not isinstance(left_val, str) else left_val.strip()
                    right_val = str(right_val).strip() if not isinstance(right_val, str) else right_val.strip()

                    # Strip quotes from literals
                    for quotes in [("'", "'"), ('"', '"')]:
                        if left_val.startswith(quotes[0]) and left_val.endswith(quotes[1]):
                            left_val = left_val[1:-1]
                        if right_val.startswith(quotes[0]) and right_val.endswith(quotes[1]):
                            right_val = right_val[1:-1]

                    if op == '==':
                        return left_val == right_val
                    elif op == '!=':
                        return left_val != right_val
                    elif op in ('>', '<', '>=', '<='):
                        try:
                            l, r = float(left_val), float(right_val)
                            return (l > r if op == '>' else l < r if op == '<' else
                                    l >= r if op == '>=' else l <= r)
                        except (ValueError, TypeError):
                            return (left_val > right_val if op == '>' else
                                    left_val < right_val if op == '<' else
                                    left_val >= right_val if op == '>=' else
                                    left_val <= right_val)

            resolved = self._apply_databinding(condition)
            if isinstance(resolved, bool):
                return resolved
            if isinstance(resolved, str):
                return resolved.lower() not in ('', 'false', '0', 'null', 'undefined', '{error')
            if isinstance(resolved, (int, float)):
                return resolved != 0
            return bool(resolved)
        except Exception:
            return False

    HTMLRenderer._evaluate_condition = patched_renderer_evaluate_condition

    # Patch _evaluate_expression to handle dotted keys stored directly in local_vars
    original_evaluate_expression = HTMLRenderer._evaluate_expression

    def patched_evaluate_expression(self, expression):
        # First: check if the full dotted expression exists as a direct key in local_vars
        if '.' in expression and expression in self.context.local_vars:
            return self.context.local_vars[expression]
        return original_evaluate_expression(self, expression)

    HTMLRenderer._evaluate_expression = patched_evaluate_expression

    # Patch _render_text_node to handle non-string values from _apply_databinding
    original_render_text = HTMLRenderer._render_text_node

    def patched_render_text_node(self, node):
        text = node.content
        if hasattr(self, '_raw_mode') and self._raw_mode:
            return text
        if node.has_databinding:
            text = self._apply_databinding(text)
        if callable(text):
            text = ''
        return html_module.escape(str(text) if text is not None else '')

    HTMLRenderer._render_text_node = patched_render_text_node

    print("[PATCH] Renderer patched for query loops and attribute safety", flush=True)


def _patch_web_server_secret_key():
    """Ensure web server uses stable secret key from env var."""
    import sys as _sys

    wsgi_mod = _sys.modules.get('src.runtime.wsgi')
    if wsgi_mod:
        real_app = wsgi_mod.app
        secret = os.environ.get('QUANTUM_SECRET_KEY')
        if secret:
            real_app.secret_key = secret
            print(f"[PATCH] Secret key set from env var", flush=True)
