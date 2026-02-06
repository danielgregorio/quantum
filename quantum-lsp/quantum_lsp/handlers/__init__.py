"""
LSP request handlers.

Each module registers handlers for specific LSP features.
"""

from .completion import register_completion_handlers
from .hover import register_hover_handlers
from .definition import register_definition_handlers
from .references import register_references_handlers
from .diagnostics import register_diagnostics_handlers
from .formatting import register_formatting_handlers
from .symbols import register_symbols_handlers

__all__ = [
    "register_completion_handlers",
    "register_hover_handlers",
    "register_definition_handlers",
    "register_references_handlers",
    "register_diagnostics_handlers",
    "register_formatting_handlers",
    "register_symbols_handlers",
]
