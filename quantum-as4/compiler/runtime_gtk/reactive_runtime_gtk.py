"""
GTK Reactive Runtime - Desktop equivalent of reactive-runtime.js

This runtime allows MXML applications to run as native GTK desktop apps
while maintaining full compatibility with the web component architecture.

Features:
- Automatic UI updates when data changes (using Python properties)
- Two-way binding for form inputs
- Dependency tracking
- Same component API as web version
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Gdk
import re
from typing import Any, Dict, List, Callable, Set


class ReactiveObject(GObject.GObject):
    """
    Makes an object reactive - when properties change, automatically update UI.
    This is the Python/GTK equivalent of JavaScript Proxy.
    """

    def __init__(self, runtime, **kwargs):
        super().__init__()
        self._runtime = runtime
        self._properties = {}

        # Initialize properties
        for key, value in kwargs.items():
            self._properties[key] = value

    def __getattr__(self, name):
        if name.startswith('_'):
            return super().__getattribute__(name)
        return self._properties.get(name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
            return

        # Only update if value actually changed
        old_value = self._properties.get(name)
        if old_value == value:
            return

        self._properties[name] = value
        print(f"[Reactive] Property changed: {name} = {value}")

        # Trigger updates for all UI elements that depend on this property
        if hasattr(self, '_runtime'):
            self._runtime.notify_dependents(name, value)


class GTKReactiveRuntime:
    """
    GTK Runtime - Desktop equivalent of ReactiveRuntime (reactive-runtime.js)

    Renders MXML component trees as GTK widgets with reactive data binding.
    """

    def __init__(self):
        self.app = None
        self.window = None
        self.components = {}  # Component type → render function

        # Reactive system
        self.dependencies = {}  # property → Set of update functions
        self.bindings = {}  # widget → binding info
        self.currently_rendering = None

        # Component registry
        self.register_default_components()

    def set_app(self, app_data: Dict[str, Any]):
        """Set application data and make it reactive"""
        self.app = ReactiveObject(self, **app_data)
        return self.app

    def track_dependency(self, property_name: str, update_fn: Callable):
        """Track that a widget depends on a property"""
        if property_name not in self.dependencies:
            self.dependencies[property_name] = set()
        self.dependencies[property_name].add(update_fn)

    def notify_dependents(self, property_name: str, new_value: Any):
        """Notify all widgets that depend on a property"""
        if property_name in self.dependencies:
            update_fns = self.dependencies[property_name]
            print(f"[Reactive] Updating {len(update_fns)} dependent(s) for: {property_name}")

            for update_fn in update_fns:
                try:
                    update_fn(new_value)
                except Exception as e:
                    print(f"Error updating dependent: {e}")

    def evaluate_binding(self, expression: str) -> Any:
        """Evaluate binding expression like {variable} or {object.property}"""
        if not expression:
            return ''

        # Extract variable name from {variable}
        match = re.match(r'\{([^}]+)\}', expression)
        if match:
            var_name = match.group(1).strip()

            # Simple property access
            if '.' not in var_name:
                return getattr(self.app, var_name, '')

            # Nested property access (e.g., user.name)
            parts = var_name.split('.')
            value = self.app
            for part in parts:
                value = getattr(value, part, None)
                if value is None:
                    break
            return value or ''

        return expression

    def create_reactive_binding(self, widget, expression: str, property_name: str = 'label'):
        """Create a reactive binding for a widget"""
        match = re.match(r'\{([^}]+)\}', expression)
        if not match:
            return

        var_name = match.group(1).strip().split('.')[0]  # Get root variable

        # Create update function
        def update_fn(new_value):
            value = self.evaluate_binding(expression)
            if property_name == 'label':
                widget.set_label(str(value))
            elif property_name == 'text':
                widget.set_text(str(value))
            elif property_name == 'markup':
                widget.set_markup(str(value))

        # Track dependency
        self.track_dependency(var_name, update_fn)

        # Initial update
        update_fn(None)

    def setup_two_way_binding(self, widget, var_name: str):
        """Setup two-way binding for input widgets"""
        # Update app property when widget changes
        def on_changed(widget):
            if isinstance(widget, Gtk.Entry):
                value = widget.get_text()
            elif isinstance(widget, Gtk.TextView):
                buffer = widget.get_buffer()
                start, end = buffer.get_bounds()
                value = buffer.get_text(start, end, False)
            else:
                return

            # Handle nested properties
            if '.' in var_name:
                parts = var_name.split('.')
                obj = self.app
                for part in parts[:-1]:
                    obj = getattr(obj, part)
                setattr(obj, parts[-1], value)
            else:
                setattr(self.app, var_name, value)

        widget.connect('changed', on_changed)

        # Update widget when app property changes
        def update_fn(new_value):
            if isinstance(widget, Gtk.Entry):
                if widget.get_text() != str(new_value):
                    widget.set_text(str(new_value))

        self.track_dependency(var_name, update_fn)

    def render(self, component_tree: Dict, title: str = "MXML Application"):
        """Render component tree to GTK window"""
        self.window = Gtk.Window()
        self.window.set_title(title)
        self.window.connect('destroy', Gtk.main_quit)

        # Set window size if specified
        if 'props' in component_tree:
            width = component_tree['props'].get('width', 800)
            height = component_tree['props'].get('height', 600)
            if isinstance(width, str):
                width = int(width.replace('px', ''))
            if isinstance(height, str):
                height = int(height.replace('px', ''))
            self.window.set_default_size(width, height)

        # Render root component
        root_widget = self.render_component(component_tree)
        if root_widget:
            self.window.add(root_widget)

        self.window.show_all()
        return self.window

    def render_component(self, node: Dict):
        """Render a single component"""
        component_type = node.get('type', 'Unknown')
        renderer = self.components.get(component_type)

        if not renderer:
            print(f"Unknown component: {component_type}")
            return self.render_unknown(node)

        return renderer(self, node)

    def register_default_components(self):
        """Register default component renderers"""
        from .components_gtk import (
            render_application,
            render_vbox,
            render_hbox,
            render_label,
            render_button,
            render_text_input,
            render_panel,
            render_spacer,
            render_checkbox,
            render_text_area,
            render_numeric_stepper,
            render_slider,
            render_progress_bar,
            render_combobox,
        )

        self.components = {
            'Application': render_application,
            'VBox': render_vbox,
            'HBox': render_hbox,
            'Label': render_label,
            'Button': render_button,
            'TextInput': render_text_input,
            'Panel': render_panel,
            'Spacer': render_spacer,
            'CheckBox': render_checkbox,
            'TextArea': render_text_area,
            'NumericStepper': render_numeric_stepper,
            'HSlider': render_slider,
            'VSlider': render_slider,
            'Slider': render_slider,
            'ProgressBar': render_progress_bar,
            'ComboBox': render_combobox,
        }

    def render_unknown(self, node: Dict):
        """Render unknown component as placeholder"""
        label = Gtk.Label()
        label.set_markup(f'<span color="red">[Unknown: {node.get("type")}]</span>')
        frame = Gtk.Frame()
        frame.add(label)
        return frame

    def execute_handler(self, handler_code: str, *args):
        """Execute event handler"""
        if not self.app:
            return

        try:
            # Extract function name
            func_name = re.sub(r'\(.*\)', '', handler_code)

            # Get function from app
            func = getattr(self.app, func_name, None)
            if callable(func):
                func(*args)
            else:
                print(f"Handler not found: {func_name}")
        except Exception as e:
            print(f"Error executing handler: {handler_code} - {e}")

    def apply_common_props(self, widget, props: Dict):
        """Apply common properties to widgets"""
        if 'width' in props:
            width = props['width']
            if isinstance(width, str):
                width = int(width.replace('px', ''))
            widget.set_size_request(width, -1)

        if 'height' in props:
            height = props['height']
            if isinstance(height, str):
                height = int(height.replace('px', ''))
            widget.set_size_request(-1, height)

        if 'visible' in props and props['visible'] == 'false':
            widget.set_visible(False)

        if 'id' in props:
            widget.set_name(props['id'])


def run_gtk_app(component_tree: Dict, app_data: Dict = None, title: str = "MXML Application"):
    """
    Run MXML application as GTK desktop app

    Args:
        component_tree: Parsed MXML component tree
        app_data: Application data (variables, methods)
        title: Window title
    """
    runtime = GTKReactiveRuntime()

    if app_data:
        runtime.set_app(app_data)

    runtime.render(component_tree, title)
    Gtk.main()
