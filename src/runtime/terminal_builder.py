"""
Terminal Engine - Builder/Orchestrator

Orchestrates the compilation pipeline:
  ApplicationNode (type="terminal") -> extract screens/keybindings/css -> TerminalCodeGenerator -> .py file

Usage:
    builder = TerminalBuilder()
    python_code = builder.build(app_node)
    builder.build_to_file(app_node, "output.py")
"""

import os
from pathlib import Path
from typing import Optional

from core.ast_nodes import ApplicationNode
from core.features.terminal_engine.src.ast_nodes import (
    ScreenNode, KeybindingNode, ServiceNode, CssNode,
)
from runtime.terminal_code_generator import TerminalCodeGenerator


class TerminalBuildError(Exception):
    """Error during terminal app build."""
    pass


class TerminalBuilder:
    """Builds a standalone Python TUI app from a Quantum terminal ApplicationNode."""

    def build(self, app: ApplicationNode) -> str:
        """Build Python source string from an ApplicationNode with type='terminal'.

        The ApplicationNode is expected to have:
        - app.screens: list of ScreenNode
        - app.terminal_css: str (optional)
        - app.keybindings: list of KeybindingNode (optional)
        - app.services: list of ServiceNode (optional)
        """
        screens = getattr(app, 'screens', [])
        terminal_css = getattr(app, 'terminal_css', '')
        keybindings = getattr(app, 'keybindings', [])
        services = getattr(app, 'services', [])

        if not screens:
            raise TerminalBuildError("No screens found in terminal application")

        valid_screens = [s for s in screens if isinstance(s, ScreenNode)]
        if not valid_screens:
            raise TerminalBuildError("No valid ScreenNode found in terminal application")

        generator = TerminalCodeGenerator()
        python_code = generator.generate(
            screens=valid_screens,
            title=app.app_id,
            terminal_css=terminal_css,
            keybindings=[k for k in keybindings if isinstance(k, KeybindingNode)],
            services=[s for s in services if isinstance(s, ServiceNode)],
        )
        return python_code

    def build_to_file(self, app: ApplicationNode, output_path: Optional[str] = None) -> str:
        """Build and write .py file. Returns the output file path."""
        python_code = self.build(app)

        if output_path is None:
            output_path = f"{app.app_id}.py"

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(python_code, encoding='utf-8')

        return str(path.resolve())
