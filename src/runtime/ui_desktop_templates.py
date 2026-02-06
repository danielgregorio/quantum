"""
UI Engine - Desktop Templates

Provides templates for Python pywebview desktop apps with JS bridge:
  - QUANTUM_STATE_CLASS: Reactive state container with JS notification
  - QUANTUM_API_CLASS: API class template exposed to JavaScript
  - JS_BRIDGE_CODE: JavaScript bridge for Python-JS communication
  - DESKTOP_TEMPLATE: Complete Python pywebview app template
"""

from typing import Any, Dict


# ==========================================================================
# QuantumState Class - Reactive state container
# ==========================================================================

QUANTUM_STATE_CLASS = '''\
class QuantumState:
    """Reactive state container with JS notification and persistence support."""

    def __init__(self, window_ref, persist_config: Dict[str, Dict] = None):
        self._window = window_ref
        self._state: Dict[str, Any] = {}
        self._persist_config = persist_config or {}  # name -> {scope, key, ttl, encrypt}
        self._storage_path = None

    def set(self, name: str, value: Any):
        """Set a state value and notify JS."""
        self._state[name] = value
        self._notify_js(name, value)
        # Auto-persist if configured
        if name in self._persist_config:
            self._persist_value(name, value)

    def get(self, name: str, default: Any = None) -> Any:
        """Get a state value."""
        return self._state.get(name, default)

    def _notify_js(self, name: str, value: Any):
        """Push state update to JS."""
        if self._window:
            import json
            js_value = json.dumps(value)
            self._window.evaluate_js(
                f"window.__quantumStateUpdate(\\'{name}\\', {js_value})"
            )

    def _get_storage_path(self) -> str:
        """Get the storage path for file-based persistence."""
        if self._storage_path:
            return self._storage_path
        import os
        import sys
        # Use user data directory based on platform
        if sys.platform == 'win32':
            base = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        elif sys.platform == 'darwin':
            base = os.path.expanduser('~/Library/Application Support')
        else:
            base = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
        self._storage_path = os.path.join(base, 'quantum_app', 'persist')
        os.makedirs(self._storage_path, exist_ok=True)
        return self._storage_path

    def _persist_value(self, name: str, value: Any):
        """Persist a value to storage based on configuration."""
        import json
        import os
        config = self._persist_config.get(name, {})
        scope = config.get('scope', 'local')
        key = config.get('key', name)
        ttl = config.get('ttl')

        storage_path = self._get_storage_path()
        file_path = os.path.join(storage_path, f'{key}.json')

        data = {'value': value}
        if ttl:
            import time
            data['_ttl'] = int(time.time()) + ttl

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception as e:
            print(f'Persist error for {name}: {e}')

    def _restore_persisted(self, name: str) -> Any:
        """Restore a persisted value from storage."""
        import json
        import os
        config = self._persist_config.get(name, {})
        key = config.get('key', name)

        storage_path = self._get_storage_path()
        file_path = os.path.join(storage_path, f'{key}.json')

        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check TTL expiration
            if '_ttl' in data:
                import time
                if time.time() > data['_ttl']:
                    os.remove(file_path)
                    return None

            return data.get('value')
        except Exception as e:
            print(f'Restore error for {name}: {e}')
            return None

    def restore_all_persisted(self):
        """Restore all persisted values on startup."""
        for name in self._persist_config:
            value = self._restore_persisted(name)
            if value is not None:
                self._state[name] = value
                self._notify_js(name, value)

    def remove_persisted(self, name: str):
        """Remove a persisted value from storage."""
        import os
        config = self._persist_config.get(name, {})
        key = config.get('key', name)

        storage_path = self._get_storage_path()
        file_path = os.path.join(storage_path, f'{key}.json')

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f'Remove persist error for {name}: {e}')
'''


# ==========================================================================
# QuantumAPI Class Template - API exposed to JavaScript
# ==========================================================================

QUANTUM_API_CLASS = '''\
class QuantumAPI:
    """API exposed to JavaScript via pywebview."""

    def __init__(self):
        self._window = None
        self.state = None
        self._persist_config = {persist_config}

    def _set_window(self, window):
        """Initialize window reference and state with persistence."""
        self._window = window
        self.state = QuantumState(window, self._persist_config)
        # Restore persisted values first
        self.state.restore_all_persisted()
        # State initialization
{state_init}

    def __set_state(self, args):
        """Internal: two-way binding from JS inputs."""
        name = args.get('name') if isinstance(args, dict) else None
        value = args.get('value') if isinstance(args, dict) else None
        if name:
            self.state.set(name, value)

{function_methods}
'''


# ==========================================================================
# JavaScript Bridge Code
# ==========================================================================

JS_BRIDGE_CODE = '''\
<script>
// Quantum Desktop Bridge
window.__quantumState = {};
window.__quantumBindings = {};

// Called by Python when state changes
window.__quantumStateUpdate = function(name, value) {
    window.__quantumState[name] = value;
    var bindings = window.__quantumBindings[name] || [];
    bindings.forEach(function(b) {
        if (b.type === 'text') b.el.textContent = value;
        else if (b.type === 'value') b.el.value = value;
        else if (b.type === 'html') b.el.innerHTML = value;
    });
};

// Register element to receive state updates
window.__quantumBind = function(elId, stateName, type) {
    var el = document.getElementById(elId);
    if (!el) return;
    if (!window.__quantumBindings[stateName]) {
        window.__quantumBindings[stateName] = [];
    }
    window.__quantumBindings[stateName].push({el: el, type: type || 'text'});
};

// Wrapper to call Python functions
window.__quantumCall = async function(fn, args) {
    if (window.pywebview && window.pywebview.api && window.pywebview.api[fn]) {
        return await window.pywebview.api[fn](args || {});
    } else {
        console.warn('Quantum: API not ready or function not found:', fn);
    }
};

// Form data collector
window.__quantumFormData = function(form) {
    var data = {};
    var formData = new FormData(form);
    formData.forEach(function(value, key) {
        data[key] = value;
    });
    return data;
};
</script>
'''


# ==========================================================================
# Desktop App Template
# ==========================================================================

DESKTOP_TEMPLATE = '''\
"""Quantum UI Desktop App - Generated pywebview Application

This file was generated by the Quantum UI Engine.
It creates a native desktop window using pywebview with
bidirectional Python-JS communication.
"""

import webview
from typing import Dict, Any


{quantum_state_class}


{quantum_api_class}


def main():
    """Main entry point for the desktop application."""
    html_content = {html_content}

    # Create API instance
    api = QuantumAPI()

    # Create window with API
    window = webview.create_window(
        title={title},
        html=html_content,
        width={width},
        height={height},
        js_api=api,
    )

    # Set window reference after creation
    def on_loaded():
        api._set_window(window)

    window.events.loaded += on_loaded

    # Start the application
    webview.start()


if __name__ == "__main__":
    main()
'''


# ==========================================================================
# Helper functions for code generation
# ==========================================================================

def escape_for_python_string(s: str) -> str:
    """Escape a string for use in a Python triple-quoted string."""
    # Replace backslashes first, then other special chars
    s = s.replace('\\', '\\\\')
    s = s.replace("'''", "\\'\\'\\'")
    return s


def indent_code(code: str, spaces: int = 8) -> str:
    """Indent each line of code by the specified number of spaces."""
    indent = ' ' * spaces
    lines = code.split('\n')
    return '\n'.join(indent + line if line.strip() else line for line in lines)
