"""
CLI Reactive Runtime - Terminal/Console equivalent of reactive-runtime.js

This runtime allows MXML applications to run as CLI applications in the terminal
with text-based UI, maintaining compatibility with the component architecture.

Features:
- Text-based UI using print() and input()
- Interactive prompts for user input
- Automatic re-rendering on data changes
- Same component API as web and desktop versions
"""

import os
import sys
from typing import Any, Dict, List, Callable, Set


class ReactiveObject:
    """
    Makes an object reactive - when properties change, automatically update UI.
    CLI version uses callbacks to trigger re-render.
    """

    def __init__(self, runtime, **kwargs):
        object.__setattr__(self, '_runtime', runtime)
        object.__setattr__(self, '_properties', {})

        # Initialize properties
        for key, value in kwargs.items():
            self._properties[key] = value

    def __getattr__(self, name):
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        return self._properties.get(name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
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


class CLIReactiveRuntime:
    """
    CLI Runtime - Terminal equivalent of ReactiveRuntime

    Renders MXML component trees as text-based CLI interface.
    """

    def __init__(self):
        self.app = None
        self.components = {}  # Component type → render function

        # Reactive system
        self.dependencies = {}  # property → Set of update functions
        self.bindings = {}  # element → binding info
        self.currently_rendering = None

        # UI state
        self.rendered_output = []
        self.menu_items = []  # List of (label, handler) tuples

        # Component registry
        self.register_default_components()

    def set_app(self, app_data: Dict[str, Any]):
        """Set application data and make it reactive"""
        self.app = ReactiveObject(self, **app_data)
        return self.app

    def track_dependency(self, property_name: str, update_fn: Callable):
        """Track that an element depends on a property"""
        if property_name not in self.dependencies:
            self.dependencies[property_name] = set()
        self.dependencies[property_name].add(update_fn)

    def notify_dependents(self, property_name: str, new_value: Any):
        """Notify all elements that depend on a property"""
        if property_name in self.dependencies:
            update_fns = self.dependencies[property_name]
            print(f"[Reactive] Updating {len(update_fns)} dependent(s) for: {property_name}")

            # Re-render the entire UI
            self.render_ui()

    def evaluate_binding(self, expression: str) -> Any:
        """Evaluate binding expression like {variable} or {object.property}"""
        if not expression:
            return ''

        # Extract variable name from {variable}
        import re
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

    def render(self, component_tree: Dict, title: str = "MXML Application"):
        """Render component tree as CLI application"""
        self.component_tree = component_tree
        self.title = title

        # Initial render
        self.render_ui()

        # Start interactive loop
        self.run_interactive_loop()

    def render_ui(self):
        """Render the UI to terminal"""
        # Clear screen
        os.system('clear' if os.name == 'posix' else 'cls')

        # Reset state
        self.rendered_output = []
        self.menu_items = []

        # Render title
        print("=" * 60)
        print(f"  {self.title}")
        print("=" * 60)
        print()

        # Render component tree
        self.render_component(self.component_tree)

        # Print all output
        for line in self.rendered_output:
            print(line)

        # Show menu if there are interactive items
        if self.menu_items:
            print()
            print("-" * 60)
            print("Options:")
            for idx, (label, _) in enumerate(self.menu_items, 1):
                print(f"  {idx}. {label}")
            print("  0. Exit")
            print("-" * 60)

    def run_interactive_loop(self):
        """Run interactive command loop"""
        while True:
            if self.menu_items:
                try:
                    choice = input("\nEnter choice: ").strip()

                    if choice == '0':
                        print("Goodbye!")
                        break

                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(self.menu_items):
                        _, handler = self.menu_items[choice_idx]
                        handler()
                        # Re-render after action
                        self.render_ui()
                    else:
                        print("Invalid choice!")
                except ValueError:
                    print("Please enter a number!")
                except KeyboardInterrupt:
                    print("\nGoodbye!")
                    break
            else:
                # No interactive items, just display and exit
                input("\nPress Enter to exit...")
                break

    def render_component(self, node: Dict):
        """Render a single component"""
        component_type = node.get('type', 'Unknown')
        renderer = self.components.get(component_type)

        if not renderer:
            self.rendered_output.append(f"[Unknown: {component_type}]")
            return

        renderer(self, node)

    def register_default_components(self):
        """Register default component renderers"""
        from .components_cli import (
            render_application,
            render_vbox,
            render_hbox,
            render_label,
            render_button,
            render_text_input,
            render_panel,
            render_spacer,
            render_checkbox,
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
        }

    def execute_handler(self, handler_code: str, *args):
        """Execute event handler"""
        if not self.app:
            return

        try:
            # Extract function name
            import re
            func_name = re.sub(r'\(.*\)', '', handler_code)

            # Get function from app
            func = getattr(self.app, func_name, None)
            if callable(func):
                func(*args)
            else:
                print(f"Handler not found: {func_name}")
        except Exception as e:
            print(f"Error executing handler: {handler_code} - {e}")


def run_cli_app(component_tree: Dict, app_data: Dict = None, title: str = "MXML Application"):
    """
    Run MXML application as CLI application

    Args:
        component_tree: Parsed MXML component tree
        app_data: Application data (variables, methods)
        title: Application title
    """
    runtime = CLIReactiveRuntime()

    if app_data:
        runtime.set_app(app_data)

    runtime.render(component_tree, title)
