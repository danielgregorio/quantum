"""
Quantum Dashboard - App Startup

Initializes SQLite database and applies runtime patches.
Called automatically by wsgi.py before the web server starts.
"""

import os
import sys
import sqlite3
from pathlib import Path


def run():
    """Entry point called by wsgi.py startup hook."""
    _init_database()
    _patch_execution_context()
    # _patch_component_runtime() removed — see the note below.
    _patch_database_service()
    print("[STARTUP] Quantum Dashboard initialized", flush=True)


def _patch_database_service():
    """Patch DatabaseService to always have local datasources from config."""
    import yaml
    from runtime.database_service import DatabaseService

    config_path = Path('/app/quantum.config.yaml')
    if not config_path.exists():
        config_path = Path('quantum.config.yaml')

    local_ds = {}
    if config_path.exists():
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
        local_ds = cfg.get('datasources', {})

    if not local_ds:
        return

    original_init = DatabaseService.__init__

    def patched_init(self, admin_api_url="http://localhost:8000", **kwargs):
        original_init(self, admin_api_url=admin_api_url)
        if not hasattr(self, 'local_datasources') or not self.local_datasources:
            self.local_datasources = {}
        self.local_datasources.update(local_ds)

    DatabaseService.__init__ = patched_init

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
    print(f"[STARTUP] DatabaseService patched with datasources: {list(local_ds.keys())}", flush=True)


def _init_database():
    """Create SQLite database and seed initial data."""
    # Read the actual database path from quantum.config.yaml
    import yaml
    config_path = Path('/app/quantum.config.yaml')
    if not config_path.exists():
        config_path = Path('quantum.config.yaml')

    db_path_str = '/app/data/tasks.db'
    if config_path.exists():
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
        ds = cfg.get('datasources', {}).get('taskdb', {})
        db_path_str = ds.get('database', db_path_str)

    db_path = Path(db_path_str)

    # Ensure parent directory exists
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Container may not have write permission; use /tmp fallback
        fallback_dir = Path('/tmp/quantum-data')
        fallback_dir.mkdir(parents=True, exist_ok=True)
        db_path = fallback_dir / 'tasks.db'
        # Update config file to reflect actual path
        if config_path.exists():
            cfg['datasources']['taskdb']['database'] = str(db_path)
            try:
                with open(config_path, 'w') as f:
                    yaml.dump(cfg, f, default_flow_style=False)
                print(f"[DB] Updated config to use fallback path: {db_path}", flush=True)
            except PermissionError:
                # Config file is read-only; set env var for runtime to pick up
                os.environ['QUANTUM_TASKDB_PATH'] = str(db_path)
                print(f"[DB] Set QUANTUM_TASKDB_PATH={db_path}", flush=True)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

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
