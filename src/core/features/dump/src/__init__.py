"""
Dump feature for Quantum Language

Provides beautiful variable inspection for debugging,
like ColdFusion's cfdump but better.
"""

from .ast_node import DumpNode
from .parser import parse_dump
from .runtime import DumpService

__all__ = ['DumpNode', 'parse_dump', 'DumpService']
