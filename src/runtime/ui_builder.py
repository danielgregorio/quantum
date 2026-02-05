"""
UI Engine - Builder/Orchestrator

Orchestrates the compilation pipeline:
  ApplicationNode (type="ui") -> extract UI nodes -> Adapter -> output file

Supports multiple targets:
  - html: HTML/CSS standalone page
  - textual: Python Textual TUI application
  - desktop: Python pywebview desktop application

Usage:
    builder = UIBuilder()
    code = builder.build(app_node, target='html')
    builder.build_to_file(app_node, target='textual', output_path='app.py')
"""

from pathlib import Path
from typing import Optional

from core.ast_nodes import ApplicationNode
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

        if target == 'html':
            from runtime.ui_html_adapter import UIHtmlAdapter
            adapter = UIHtmlAdapter()
            return adapter.generate(windows, ui_children, title)
        elif target == 'textual':
            from runtime.ui_textual_adapter import UITextualAdapter
            adapter = UITextualAdapter()
            return adapter.generate(windows, ui_children, title)
        elif target == 'desktop':
            from runtime.ui_desktop_adapter import UIDesktopAdapter
            adapter = UIDesktopAdapter()
            return adapter.generate(windows, ui_children, title)
        else:
            raise UIBuildError(f"Unknown target: {target}. Must be html, textual, or desktop")

    def build_to_file(self, app: ApplicationNode, target: str = 'html',
                      output_path: Optional[str] = None) -> str:
        """Build and write output file. Returns the output file path."""
        code = self.build(app, target)

        if output_path is None:
            ext = '.html' if target == 'html' else '.py'
            output_path = f"{app.app_id}{ext}"

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code, encoding='utf-8')

        return str(path.resolve())
