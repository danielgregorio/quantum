"""
UI Engine - Builder/Orchestrator

Orchestrates the compilation pipeline:
  ApplicationNode (type="ui") -> extract UI nodes -> Adapter -> output file

Targets (UI-8):
  - html: a standalone HTML/CSS page — layout only
  - textual: a standalone Python Textual app — layout only

--target mobile (React Native, which translated the logic to JavaScript of its own) was removed: a phone's
application is the TUI as a hosted application's client, `quantum package --target android|ios` (UI-22).

The application's logic runs in pages: a <q:component> with ui:* served by
`quantum start`, drawn by `quantum console` and `quantum desktop` too. The
old desktop target (a pywebview app that translated the logic to a JS bridge)
was removed in 0.16: `quantum desktop` opens the pages in a window.

Usage:
    builder = UIBuilder()
    code = builder.build(app_node, target='html')
    builder.build_to_file(app_node, target='textual', output_path='app.py')
"""

from pathlib import Path
from typing import Optional

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
        if target in ('mobile', 'react-native'):
            raise UIBuildError(
                f'--target {target} (React Native) was removed: it translated the logic to JavaScript of its '
                f'own. A phone\'s application is the TUI as a hosted application\'s client: '
                f'`quantum package <app> --server https://... --target android|ios` (UI-22).')
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
        else:
            raise UIBuildError(f"Unknown target: {target}. Must be html or textual")

    def build_to_file(self, app: ApplicationNode, target: str = 'html',
                      output_path: Optional[str] = None) -> str:
        """Build and write output file. Returns the output file path."""
        code = self.build(app, target)

        if output_path is None:
            # UI-0: one file per target. textual and desktop both wrote
            # <id>.py, so building one erased the other.
            suffix = {'html': '.html', 'textual': '_console.py',
                      }.get(target, '.py')
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
