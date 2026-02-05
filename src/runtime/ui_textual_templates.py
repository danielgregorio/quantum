"""
UI Engine - Textual Templates

Provides:
  - PyBuilder reuse from terminal_templates
  - UI_TEXTUAL_APP_TEMPLATE: Textual app template for UI engine
"""

from runtime.terminal_templates import PyBuilder, py_string, py_id, py_bool


# ==========================================================================
# Textual App Template
# ==========================================================================

UI_TEXTUAL_APP_TEMPLATE = '''\
"""Quantum UI App - Generated Textual Application"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Grid, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, Button, Input, DataTable,
    Checkbox, Switch, ProgressBar, Tree, RichLog, Rule,
    LoadingIndicator, Markdown, TabbedContent, TabPane,
    Collapsible, OptionList, Select, Label,
)

{extra_imports}

class QuantumUIApp(App):
    """Quantum UI Application"""

    TITLE = {title}
    CSS = """{css}"""

{bindings}
    def compose(self) -> ComposeResult:
{compose_body}

{methods}

if __name__ == "__main__":
    app = QuantumUIApp()
    app.run()
'''
