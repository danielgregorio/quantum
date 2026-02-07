"""
UI Engine - Builder/Orchestrator

Orchestrates the compilation pipeline:
  ApplicationNode (type="ui") -> extract UI nodes -> Adapter -> output file

Supports multiple targets:
  - html: HTML/CSS standalone page
  - textual: Python Textual TUI application
  - desktop: Python pywebview desktop application (with JS bridge)
  - mobile / react-native: React Native mobile application

Usage:
    builder = UIBuilder()
    code = builder.build(app_node, target='html')
    builder.build_to_file(app_node, target='textual', output_path='app.py')
    builder.build_to_file(app_node, target='mobile', output_path='App.js')
"""

from pathlib import Path
from typing import Optional, Dict, Any, List

from core.ast_nodes import ApplicationNode
from core.features.state_management.src.ast_node import SetNode
from core.features.functions.src.ast_node import FunctionNode
from core.features.ui_engine.src.ast_nodes import UIWindowNode


class UIBuildError(Exception):
    """Error during UI app build."""
    pass


class UIBuilder:
    """Builds multi-target UI output from a Quantum UI ApplicationNode."""

    def build(self, app: ApplicationNode, target: str = 'html') -> str:
        """Build output string from an ApplicationNode with type='ui'.

        Args:
            app: ApplicationNode with ui_windows and ui_children populated.
            target: 'html', 'textual', or 'desktop'.

        Returns:
            Generated source code string.
        """
        windows = getattr(app, 'ui_windows', [])
        ui_children = getattr(app, 'ui_children', [])
        title = app.app_id or 'Quantum UI'

        if not windows and not ui_children:
            raise UIBuildError("No UI elements found in application")

        # Get theme from application
        theme = getattr(app, 'ui_theme', None)

        if target == 'html':
            from runtime.ui_html_adapter import UIHtmlAdapter
            adapter = UIHtmlAdapter()
            return adapter.generate(windows, ui_children, title, theme=theme)
        elif target == 'textual':
            from runtime.ui_textual_adapter import UITextualAdapter
            adapter = UITextualAdapter()
            return adapter.generate(windows, ui_children, title)
        elif target == 'desktop':
            from runtime.ui_desktop_adapter import UIDesktopAdapter
            adapter = UIDesktopAdapter()

            # Extract functions and state for desktop bridge
            functions = self._extract_functions(app)
            state_vars = self._extract_state(app)

            return adapter.generate(
                windows, ui_children, title,
                functions=functions,
                state_vars=state_vars
            )
        elif target in ('mobile', 'react-native'):
            from runtime.ui_mobile_adapter import UIReactNativeAdapter
            adapter = UIReactNativeAdapter()

            # Extract functions and state for React Native hooks
            functions = self._extract_functions(app)
            state_vars = self._extract_state(app)

            return adapter.generate(
                windows, ui_children, title,
                functions=functions,
                state_vars=state_vars
            )
        else:
            raise UIBuildError(f"Unknown target: {target}. Must be html, textual, desktop, or mobile")

    def build_to_file(self, app: ApplicationNode, target: str = 'html',
                      output_path: Optional[str] = None) -> str:
        """Build and write output file. Returns the output file path."""
        code = self.build(app, target)

        if output_path is None:
            if target == 'html':
                ext = '.html'
            elif target in ('mobile', 'react-native'):
                ext = '.js'
            else:
                ext = '.py'
            output_path = f"{app.app_id}{ext}"

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code, encoding='utf-8')

        return str(path.resolve())

    def _extract_functions(self, app: ApplicationNode) -> Dict[str, FunctionNode]:
        """Extract q:function nodes from application.

        Only extracts UI functions (those without REST endpoints),
        as REST functions are for server-side use.

        Args:
            app: ApplicationNode to extract functions from.

        Returns:
            Dict mapping function name to FunctionNode.
        """
        functions = {}

        # Check components for functions
        for component in getattr(app, 'components', []):
            for func in getattr(component, 'functions', []):
                # Only include UI functions (not REST endpoints)
                if not func.is_rest_enabled():
                    functions[func.name] = func

        # Check for functions directly on app (if any)
        for func in getattr(app, 'functions', []):
            if not func.is_rest_enabled():
                functions[func.name] = func

        # Check ui_children for functions (when parsed directly into app)
        for child in getattr(app, 'ui_children', []):
            if isinstance(child, FunctionNode) and not child.is_rest_enabled():
                functions[child.name] = child

        # Check ui_windows children for functions
        for window in getattr(app, 'ui_windows', []):
            for child in getattr(window, 'children', []):
                if isinstance(child, FunctionNode) and not child.is_rest_enabled():
                    functions[child.name] = child

        return functions

    def _extract_state(self, app: ApplicationNode) -> Dict[str, Any]:
        """Extract q:set nodes from application level.

        Extracts initial state variables defined at the application or
        component level for state initialization.

        Args:
            app: ApplicationNode to extract state from.

        Returns:
            Dict mapping variable name to initial value.
        """
        state = {}

        # Check ui_children for SetNode (top-level state declarations)
        for child in getattr(app, 'ui_children', []):
            if isinstance(child, SetNode):
                # Use default if value is not set
                value = child.value if child.value is not None else child.default
                state[child.name] = value

        # Check ui_windows children for SetNode
        for window in getattr(app, 'ui_windows', []):
            for child in getattr(window, 'children', []):
                if isinstance(child, SetNode):
                    value = child.value if child.value is not None else child.default
                    state[child.name] = value

        # Check components for statements that are SetNode
        for component in getattr(app, 'components', []):
            for stmt in getattr(component, 'statements', []):
                if isinstance(stmt, SetNode):
                    value = stmt.value if stmt.value is not None else stmt.default
                    state[stmt.name] = value

        return state
