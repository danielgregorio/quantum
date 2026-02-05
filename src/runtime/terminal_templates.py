"""
Terminal Engine - Python Code Templates and PyBuilder

Provides:
  - PyBuilder: Structured Python code emitter with proper indentation
  - App template for Textual applications
"""


# ==========================================================================
# PyBuilder - Structured Python code emitter
# ==========================================================================

class PyBuilder:
    """Builds syntactically valid Python code with proper indentation.

    Every append method returns self for chaining.
    """

    def __init__(self, indent_size: int = 4):
        self._lines: list[str] = []
        self._indent: int = 0
        self._indent_size: int = indent_size

    # -- core --

    @property
    def _pad(self) -> str:
        return ' ' * (self._indent * self._indent_size)

    def line(self, code: str = '') -> 'PyBuilder':
        """Emit a single line at current indent."""
        self._lines.append(f"{self._pad}{code}" if code else '')
        return self

    def raw(self, code: str) -> 'PyBuilder':
        """Emit raw code at current indent (multi-line)."""
        for ln in code.split('\n'):
            self._lines.append(f"{self._pad}{ln}")
        return self

    def blank(self) -> 'PyBuilder':
        self._lines.append('')
        return self

    def comment(self, text: str) -> 'PyBuilder':
        return self.line(f"# {text}")

    def section(self, title: str) -> 'PyBuilder':
        return self.blank().line(f"# === {title} ===")

    def indent(self) -> 'PyBuilder':
        self._indent += 1
        return self

    def dedent(self) -> 'PyBuilder':
        self._indent = max(0, self._indent - 1)
        return self

    # -- Python constructs --

    def assign(self, target: str, value: str) -> 'PyBuilder':
        return self.line(f"{target} = {value}")

    def class_def(self, name: str, bases: str = '') -> 'PyBuilder':
        """Open a class definition."""
        if bases:
            self.line(f"class {name}({bases}):")
        else:
            self.line(f"class {name}:")
        self._indent += 1
        return self

    def method_def(self, name: str, params: str = 'self') -> 'PyBuilder':
        """Open a method definition."""
        self.line(f"def {name}({params}):")
        self._indent += 1
        return self

    def async_method_def(self, name: str, params: str = 'self') -> 'PyBuilder':
        """Open an async method definition."""
        self.line(f"async def {name}({params}):")
        self._indent += 1
        return self

    def func_def(self, name: str, params: str = '') -> 'PyBuilder':
        """Open a function definition."""
        self.line(f"def {name}({params}):")
        self._indent += 1
        return self

    def if_block(self, condition: str) -> 'PyBuilder':
        self.line(f"if {condition}:")
        self._indent += 1
        return self

    def elif_block(self, condition: str) -> 'PyBuilder':
        self._indent = max(0, self._indent - 1)
        self.line(f"elif {condition}:")
        self._indent += 1
        return self

    def else_block(self) -> 'PyBuilder':
        self._indent = max(0, self._indent - 1)
        self.line("else:")
        self._indent += 1
        return self

    def for_block(self, var: str, iterable: str) -> 'PyBuilder':
        self.line(f"for {var} in {iterable}:")
        self._indent += 1
        return self

    def with_block(self, expr: str) -> 'PyBuilder':
        self.line(f"with {expr}:")
        self._indent += 1
        return self

    def try_block(self) -> 'PyBuilder':
        self.line("try:")
        self._indent += 1
        return self

    def except_block(self, exc: str = 'Exception as e') -> 'PyBuilder':
        self._indent = max(0, self._indent - 1)
        self.line(f"except {exc}:")
        self._indent += 1
        return self

    def end_block(self) -> 'PyBuilder':
        """Dedent to close a block."""
        self._indent = max(0, self._indent - 1)
        return self

    def decorator(self, name: str) -> 'PyBuilder':
        return self.line(f"@{name}")

    def docstring(self, text: str) -> 'PyBuilder':
        return self.line(f'"""{text}"""')

    def return_stmt(self, value: str = '') -> 'PyBuilder':
        if value:
            return self.line(f"return {value}")
        return self.line("return")

    def yield_stmt(self, value: str) -> 'PyBuilder':
        return self.line(f"yield {value}")

    def pass_stmt(self) -> 'PyBuilder':
        return self.line("pass")

    def build(self) -> str:
        return '\n'.join(self._lines)


# ==========================================================================
# Utility functions
# ==========================================================================

def py_string(value: str) -> str:
    """Safe Python string literal."""
    escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    return f'"{escaped}"'


def py_bool(value: bool) -> str:
    return "True" if value else "False"


def py_id(name: str) -> str:
    """Convert a string to a valid Python identifier."""
    result = name.replace('-', '_').replace('.', '_').replace(' ', '_')
    if result and result[0].isdigit():
        result = '_' + result
    return result


# ==========================================================================
# App template
# ==========================================================================

APP_TEMPLATE = '''#!/usr/bin/env python3
"""
{title} - Generated by Quantum Terminal Engine
Run: python {filename}
Requires: pip install textual
"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Header, Footer, Static, Button, Input,
    DataTable, ProgressBar, Tree, RichLog,
    TabbedContent, TabPane, OptionList,
)
from textual.binding import Binding
from textual.reactive import reactive
{extra_imports}

{app_code}

if __name__ == "__main__":
    app = {app_class}()
    app.run()
'''
