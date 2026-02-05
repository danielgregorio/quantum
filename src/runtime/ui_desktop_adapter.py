"""
UI Engine - Desktop Adapter (pywebview wrapper)

Wraps the HTML adapter output in a Python script that opens
a native desktop window using pywebview.
"""

from typing import List

from core.ast_nodes import QuantumNode
from runtime.ui_html_adapter import UIHtmlAdapter


DESKTOP_TEMPLATE = '''\
"""Quantum UI Desktop App - Generated pywebview Application"""

import webview


def main():
    html_content = {html_content}

    window = webview.create_window(
        title={title},
        html=html_content,
        width={width},
        height={height},
    )
    webview.start()


if __name__ == "__main__":
    main()
'''


class UIDesktopAdapter:
    """Generates Python pywebview app from UI AST nodes."""

    def generate(self, windows: List[QuantumNode], ui_children: List[QuantumNode],
                 title: str = "Quantum UI", width: int = 1024, height: int = 768) -> str:
        """Generate Python pywebview app from UI AST."""
        html_adapter = UIHtmlAdapter()
        html = html_adapter.generate(windows, ui_children, title)

        return DESKTOP_TEMPLATE.format(
            title=repr(title),
            width=width,
            height=height,
            html_content=repr(html),
        )
