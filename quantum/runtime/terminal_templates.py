"""
Terminal Engine - Python Code Templates and PyBuilder

Provides:
  - PyBuilder: Structured Python code emitter with proper indentation
  - App template for Textual applications
"""

import re


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
    """Convert a string to a valid Python identifier.

    It replaced three characters — `-`, `.` and space — and returned the rest as
    it was. An `on-click="save()"` came in here and went out as `save()`, which the
    generator then wrote as

        def action_save()(self):

    that is: the generated Python file did not COMPILE. A single button with
    parentheses — the way a call is written in every other
    language — took down the whole application at import time.

    Now everything that does not belong in an identifier becomes `_`, so this
    function can no longer produce invalid code. Whoever wants to treat
    `name(args)` as a call must use `split_call` FIRST.
    """
    result = re.sub(r'\W', '_', name or '')
    if not result:
        return '_'
    if result[0].isdigit():
        result = '_' + result
    return result


_CALL = re.compile(r'^\s*([A-Za-z_][\w.-]*)\s*\((.*)\)\s*$', re.DOTALL)


def split_call(handler: str):
    """`"save()"` -> `("save", "")`; `"save"` -> `("save", None)`.

    Returns (name, arguments), with arguments None when the handler is not
    a call. It exists because the generators compared the RAW on-click text
    with the q:function names: `"save()"` never matched
    `save`, so the user's function was not called even when it existed.
    """
    if not handler:
        return '', None
    m = _CALL.match(handler)
    if m:
        return m.group(1), m.group(2).strip()
    return handler.strip(), None


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
