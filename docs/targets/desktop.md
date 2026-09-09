# Desktop Target (pywebview)

The Desktop target generates native desktop applications using [pywebview](https://pywebview.flowrl.com/). It creates a Python application that displays your UI in a native window with bidirectional Python-JavaScript communication.

## Overview

When you build with `--target desktop`, Quantum:

1. Generates HTML using the HTML adapter with `desktop_mode=True`
2. Creates a Python file with pywebview integration
3. Sets up a JavaScript bridge for Python-JS communication
4. Implements reactive state management
5. Handles event transformation for native callbacks

## Requirements

Install pywebview:

```bash
pip install pywebview
```

Platform-specific dependencies:

- **Windows**: No additional dependencies (uses Edge WebView2)
- **macOS**: No additional dependencies (uses WebKit)
- **Linux**: Install GTK: `sudo apt install python3-gi python3-gi-cairo gir1.2-webkit2-4.0`

## Building for Desktop

```bash
# Build UI application to desktop
python src/cli/runner.py run myapp.q --target desktop

# Output is saved as {app_id}_desktop.py
# Run the desktop app
python myapp_desktop.py
```

## Generated Code Structure

The desktop adapter generates a Python file with three main components:

### 1. QuantumState Class

Manages reactive state with JavaScript notification:

```python
class QuantumState:
    """Reactive state container with JS notification."""

    def __init__(self, window_ref, persist_config=None):
        self._window = window_ref
        self._state = {}
        self._persist_config = persist_config or {}

    def set(self, name, value):
        """Set state and notify JavaScript."""
        self._state[name] = value
        self._notify_js(name, value)
        if name in self._persist_config:
            self._persist_value(name, value)

    def get(self, name, default=None):
        """Get state value."""
        return self._state.get(name, default)

    def _notify_js(self, name, value):
        """Push state update to JavaScript."""
        import json
        js_value = json.dumps(value)
        self._window.evaluate_js(
            f"window.__quantumStateUpdate('{name}', {js_value})"
        )
```

### 2. QuantumAPI Class

Exposes Python functions to JavaScript:

```python
class QuantumAPI:
    """API exposed to JavaScript via pywebview."""

    def __init__(self):
        self._window = None
        self.state = None

    def _set_window(self, window):
        """Initialize window and state."""
        self._window = window
        self.state = QuantumState(window)
        # Initialize state variables
        self.state.set('count', 0)

    # Generated from q:function nodes
    def increment(self, args=None):
        current = self.state.get('count')
        self.state.set('count', current + 1)

    def decrement(self, args=None):
        current = self.state.get('count')
        self.state.set('count', current - 1)
```

### 3. Main Entry Point

Creates the window and starts the app:

```python
def main():
    html_content = '''<!DOCTYPE html>...'''

    api = QuantumAPI()

    window = webview.create_window(
        title="My App",
        html=html_content,
        width=1024,
        height=768,
        js_api=api,
    )

    def on_loaded():
        api._set_window(window)

    window.events.loaded += on_loaded
    webview.start()

if __name__ == "__main__":
    main()
```

## Python-JavaScript Bridge

### JavaScript Bridge Code

The HTML includes a JavaScript bridge for communication:

```javascript
// Called by Python when state changes
window.__quantumStateUpdate = function(name, value) {
    window.__quantumState[name] = value;
    // Update bound elements
    var bindings = window.__quantumBindings[name] || [];
    bindings.forEach(function(b) {
        if (b.type === 'text') b.el.textContent = value;
        else if (b.type === 'value') b.el.value = value;
    });
};

// Register element for state updates
window.__quantumBind = function(elId, stateName, type) {
    var el = document.getElementById(elId);
    if (!el) return;
    window.__quantumBindings[stateName].push({el: el, type: type});
};

// Call Python functions
window.__quantumCall = async function(fn, args) {
    if (window.pywebview && window.pywebview.api[fn]) {
        return await window.pywebview.api[fn](args || {});
    }
};

// Collect form data
window.__quantumFormData = function(form) {
    var data = {};
    new FormData(form).forEach((v, k) => data[k] = v);
    return data;
};
```

### Event Transformation

In desktop mode, event handlers are transformed:

```xml
<!-- Quantum source -->
<ui:button on-click="increment">+1</ui:button>
```

```html
<!-- Generated HTML -->
<button onclick="__quantumCall('increment')">+1</button>
```

For forms with data:

```xml
<ui:form on-submit="handleSubmit">
  <ui:input bind="name" />
  <ui:button type="submit">Submit</ui:button>
</ui:form>
```

```html
<form onsubmit="event.preventDefault();__quantumCall('handleSubmit',__quantumFormData(this))">
  <input name="name" oninput="__quantumCall('__set_state',{name:'name',value:this.value})" />
  <button type="submit">Submit</button>
</form>
```

## State Management

### Reactive State

State changes automatically update the UI:

```xml
<q:set name="count" value="0" type="number" />

<ui:text>{count}</ui:text>

<q:function name="increment">
  <q:set name="count" value="{count + 1}" />
</q:function>
```

When `increment()` is called from JavaScript:
1. Python updates `state.set('count', new_value)`
2. `_notify_js()` calls JavaScript
3. JavaScript updates all bound elements

### Two-Way Binding

Input elements with `bind` attribute have two-way binding:

```xml
<ui:input bind="userName" />
<ui:text>Hello, {userName}!</ui:text>
```

- When user types, JavaScript calls Python to update state
- Python notifies JavaScript of the change
- All bound elements update automatically

### State Persistence

Desktop apps can persist state to local storage:

```xml
<q:set name="theme" value="dark" persist="local" />
<q:set name="lastVisit" value="" persist="local" persist-ttl="86400" />
```

Persistence features:
- Stored in platform-appropriate directory
- TTL (time-to-live) support
- Automatic restore on app launch

Storage locations:
- **Windows**: `%LOCALAPPDATA%/quantum_app/persist/`
- **macOS**: `~/Library/Application Support/quantum_app/persist/`
- **Linux**: `~/.local/share/quantum_app/persist/`

## Native Features

### Window Configuration

```python
window = webview.create_window(
    title="My App",
    html=html_content,
    width=1024,
    height=768,
    resizable=True,
    fullscreen=False,
    min_size=(800, 600),
)
```

### Dialog APIs

Access native dialogs through pywebview:

```python
# In your QuantumAPI class
def open_file_dialog(self, args=None):
    file_types = ('Text Files (*.txt)', 'All Files (*.*)')
    result = self._window.create_file_dialog(
        webview.OPEN_DIALOG,
        allow_multiple=False,
        file_types=file_types
    )
    return result[0] if result else None

def save_file_dialog(self, args=None):
    result = self._window.create_file_dialog(
        webview.SAVE_DIALOG,
        save_filename='document.txt'
    )
    return result
```

### System Tray (Optional)

```python
# Extend the main() function
def main():
    # ... window creation ...

    # Add system tray (requires pystray)
    try:
        from pystray import Icon, Menu, MenuItem
        from PIL import Image

        icon = Icon(
            "quantum_app",
            Image.open("icon.png"),
            menu=Menu(
                MenuItem("Show", lambda: window.show()),
                MenuItem("Exit", lambda: webview.stop())
            )
        )
        icon.run_detached()
    except ImportError:
        pass

    webview.start()
```

## Building Executables

### PyInstaller

Create standalone executables:

```bash
pip install pyinstaller

# Build executable
pyinstaller --onefile --windowed myapp_desktop.py
```

PyInstaller spec file for better control:

```python
# myapp.spec
a = Analysis(
    ['myapp_desktop.py'],
    binaries=[],
    datas=[],
    hiddenimports=['webview'],
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='MyApp',
    debug=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    icon='app.ico',
)
```

### cx_Freeze

Alternative for building executables:

```python
# setup.py
from cx_Freeze import setup, Executable

setup(
    name="MyApp",
    version="1.0",
    executables=[Executable("myapp_desktop.py", base="Win32GUI")],
)
```

Build:

```bash
python setup.py build
```

### Nuitka

High-performance compilation:

```bash
pip install nuitka

nuitka --standalone --onefile --windows-disable-console myapp_desktop.py
```

## Example: Counter App

### Quantum Source

```xml
<q:application id="counter" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <q:set name="count" value="0" type="number" persist="local" />

  <q:function name="increment">
    <q:set name="count" value="{count + 1}" />
  </q:function>

  <q:function name="decrement">
    <q:set name="count" value="{count - 1}" />
  </q:function>

  <q:function name="reset">
    <q:set name="count" value="0" />
  </q:function>

  <ui:window title="Counter App">
    <ui:vbox padding="xl" gap="lg" align="center">
      <ui:text size="2xl" weight="bold">Counter</ui:text>
      <ui:text size="xl">{count}</ui:text>
      <ui:hbox gap="md">
        <ui:button on-click="decrement" variant="secondary">-</ui:button>
        <ui:button on-click="reset">Reset</ui:button>
        <ui:button on-click="increment" variant="primary">+</ui:button>
      </ui:hbox>
    </ui:vbox>
  </ui:window>

</q:application>
```

### Generated Python (Simplified)

```python
import webview
from typing import Dict, Any

class QuantumState:
    # ... state management code ...

class QuantumAPI:
    def __init__(self):
        self._window = None
        self.state = None
        self._persist_config = {'count': {'scope': 'local', 'key': 'count'}}

    def _set_window(self, window):
        self._window = window
        self.state = QuantumState(window, self._persist_config)
        self.state.restore_all_persisted()
        if self.state.get('count') is None:
            self.state.set('count', 0)

    def increment(self, args=None):
        self.state.set('count', self.state.get('count') + 1)

    def decrement(self, args=None):
        self.state.set('count', self.state.get('count') - 1)

    def reset(self, args=None):
        self.state.set('count', 0)

def main():
    html_content = '''<!DOCTYPE html>...'''
    api = QuantumAPI()
    window = webview.create_window(
        title="Counter App",
        html=html_content,
        width=1024,
        height=768,
        js_api=api,
    )
    window.events.loaded += lambda: api._set_window(window)
    webview.start()

if __name__ == "__main__":
    main()
```

## Troubleshooting

### Window doesn't appear

- Ensure pywebview is installed correctly
- Check platform dependencies (especially Linux)
- Try running with `webview.start(debug=True)`

### JavaScript bridge not working

- Wait for window to load before calling Python
- Check browser console for errors
- Ensure function is exposed in QuantumAPI class

### State not persisting

- Check file permissions in storage directory
- Verify persist configuration
- Check for JSON serialization errors

### Performance issues

- Minimize state updates
- Use batch updates when possible
- Consider virtual scrolling for large lists

## Related

- [HTML Target](/targets/html) - Web output
- [Mobile Target](/targets/mobile) - React Native apps
- [Terminal Target](/targets/terminal) - TUI applications
- [pywebview Documentation](https://pywebview.flowrl.com/)
