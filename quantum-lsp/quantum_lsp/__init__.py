"""
Quantum LSP - Language Server Protocol implementation for Quantum Framework

This module provides IDE support for .q files including:
- Autocompletion for tags, attributes, and values
- Hover documentation
- Go to definition
- Find references
- Real-time diagnostics
- Code formatting
- Document symbols
"""

__version__ = "1.0.0"
__author__ = "Daniel"

from .server import QuantumLanguageServer, main

__all__ = ["QuantumLanguageServer", "main", "__version__"]
