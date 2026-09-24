"""
UI Engine - Builder/Orchestrator

Orchestrates the compilation pipeline:
  ApplicationNode (type="ui") -> extract UI nodes -> Adapter -> output file

Targets (UI-8):
  - html: a standalone HTML/CSS page — layout only
  - textual: a standalone Python Textual app — layout only
  - mobile / react-native: React Native (LABORATORY: it translates q:set and
    q:function to JavaScript, with no stability promise)

The application's logic runs in pages: a <q:component> with ui:* served by
`quantum start`, drawn by `quantum console` and `quantum desktop` too. The
old desktop target (a pywebview app that translated the logic to a JS bridge)
was removed in 0.16: `quantum desktop` opens the pages in a window.

Usage:
    builder = UIBuilder()
    code = builder.build(app_node, target='html')
    builder.build_to_file(app_node, target='textual', output_path='app.py')
    builder.build_to_file(app_node, target='mobile', output_path='App.js')
"""

from pathlib import Path
from typing import Optional, Dict, Any

from quantum.core.ast_nodes import ApplicationNode
from quantum.core.features.state_management.src.ast_node import SetNode
from quantum.core.features.functions.src.ast_node import FunctionNode
from quantum.core.features.ui_engine.src.ast_nodes import is_ui_node


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
        if not isinstance(app, ApplicationNode) or getattr(app, 'app_type', None) != 'ui':
            # UI-0: it used to fail with "'ComponentNode' object has no
            # attribute 'app_id'".
            raise UIBuildError(
                'a UI build needs <q:application type="ui">; this file is a '
                f'<q:{"component" if not isinstance(app, ApplicationNode) else "application"}>. '
                'Wrap the ui:window in <q:application id="MyApp" type="ui">.')
        windows = getattr(app, 'ui_windows', [])
        ui_children = getattr(app, 'ui_children', [])
        title = app.app_id or 'Quantum UI'

        if not windows and not ui_children:
            raise UIBuildError("No UI elements found in application")

        # Get theme from application
        theme = getattr(app, 'ui_theme', None)

        if target == 'desktop':
            raise UIBuildError(
                '--target desktop was removed in Quantum 0.16: it translated the logic to a '
                'JavaScript bridge of its own. Write the screens as pages (<q:component> with '
                'ui:* in components/) and run `quantum desktop` — the same pages, in a window.')
        if target in ('html', 'textual'):
            self._layout_only(app, target)

        if target == 'html':
            from quantum.runtime.ui_html_adapter import UIHtmlAdapter
            adapter = UIHtmlAdapter()
            return adapter.generate(windows, ui_children, title, theme=theme)
        elif target == 'textual':
            from quantum.runtime.ui_textual_adapter import UITextualAdapter
            adapter = UITextualAdapter()
            return adapter.generate(windows, ui_children, title)
        elif target in ('mobile', 'react-native'):
            from quantum.core.tiers import warn_ui_target
            from quantum.runtime.ui_mobile_adapter import UIReactNativeAdapter
            warn_ui_target(target)
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
            raise UIBuildError(f"Unknown target: {target}. Must be html, textual or mobile")

    def build_to_file(self, app: ApplicationNode, target: str = 'html',
                      output_path: Optional[str] = None) -> str:
        """Build and write output file. Returns the output file path."""
        code = self.build(app, target)

        if output_path is None:
            # UI-0: one file per target. textual and desktop both wrote
            # <id>.py, so building one erased the other.
            suffix = {'html': '.html', 'textual': '_console.py',
                      'mobile': '.js', 'react-native': '.js'}.get(target, '.py')
            output_path = f"{app.app_id}{suffix}"

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code, encoding='utf-8')

        return str(path.resolve())

    def _layout_only(self, app: ApplicationNode, target: str) -> None:
        """UI-8: html and textual builds draw layout; logic in them is an error.

        It used to be dropped without a word — `{count}` came out raw and a
        button called a function that did not exist.
        """
        logic = [f'<q:function name="{f.name}">' for f in getattr(app, 'functions', [])]
        logic += [f'<q:set name="{v.name}">' for v in getattr(app, 'state_vars', [])]

        def walk(nodes):
            for node in nodes or []:
                if is_ui_node(node):
                    walk(getattr(node, 'children', None))
                elif isinstance(node, (SetNode, FunctionNode)):
                    logic.append(f'<q:{"set" if isinstance(node, SetNode) else "function"} name="{node.name}">')
                elif type(node).__name__ not in ('TextNode', 'HTMLNode', 'CommentNode'):
                    logic.append(f'<q:{type(node).__name__.replace("Node", "").lower()}>')

        walk(getattr(app, 'ui_windows', []))
        walk(getattr(app, 'ui_children', []))
        if logic:
            raise UIBuildError(
                f'a {target} UI build draws layout only, and {logic[0]} would not run in it. '
                'Write the screen as a page — <q:component> with ui:* in components/ — '
                'and run it with `quantum start`, `quantum console` or `quantum desktop`, '
                "where the page's runtime runs its logic.")

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
