"""
Diagnostics handler for textDocument/publishDiagnostics.

Provides linting for:
- Missing required attributes
- Invalid attribute values
- Unclosed tags
- Undefined variables
- Unknown tags
"""

import logging
import re
from typing import List

from lsprotocol import types

from ..schema import get_tag_info, QUANTUM_TAGS
from ..schema.attributes import get_required_attributes, validate_attribute_value

logger = logging.getLogger("quantum-lsp")


def register_diagnostics_handlers(server):
    """Register diagnostics handlers with the server."""

    # Diagnostics are primarily published through document lifecycle events
    # (open, change, save) in the workspace analyzer.

    # This module provides additional validation utilities.

    pass


def validate_document(doc) -> List[types.Diagnostic]:
    """
    Validate a document and return diagnostics.

    This is called by the workspace analyzer when documents change.
    """
    diagnostics = []

    # Get basic diagnostics from document
    diagnostics.extend(doc.get_diagnostics())

    # Additional validation
    diagnostics.extend(_validate_variable_usage(doc))
    diagnostics.extend(_validate_function_calls(doc))

    return diagnostics


def _validate_variable_usage(doc) -> List[types.Diagnostic]:
    """Check for undefined variable references."""
    diagnostics = []

    # Get all defined variable names
    defined_vars = set()
    for symbol in doc.symbols.get_variables():
        defined_vars.add(symbol.name)
    for symbol in doc.symbols.get_symbols_by_kind(doc.symbols._by_kind):
        pass  # Parameters are implicitly available

    # Get queries (they define result variables)
    for symbol in doc.symbols.get_queries():
        defined_vars.add(symbol.name)

    # Check databinding references
    ref_pattern = re.compile(r'\{([a-zA-Z_][\w.]*)\}')

    for i, line in enumerate(doc.lines):
        for match in ref_pattern.finditer(line):
            var_ref = match.group(1).split('.')[0]

            # Skip common built-ins
            if var_ref in ('true', 'false', 'null', 'undefined'):
                continue

            # Check if defined
            if var_ref not in defined_vars:
                # Check if it might be a loop variable or parameter
                # (We can't always detect these statically)
                # For now, report as hint rather than warning
                pass  # Skip for now - too many false positives

    return diagnostics


def _validate_function_calls(doc) -> List[types.Diagnostic]:
    """Check for undefined function calls."""
    diagnostics = []

    # Get all defined function names
    defined_funcs = set()
    for symbol in doc.symbols.get_functions():
        defined_funcs.add(symbol.name)

    # We could check invoke statements here
    # For now, skip to avoid false positives

    return diagnostics
