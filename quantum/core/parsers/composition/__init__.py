"""
Component Composition Parsers

Parsers for component composition tags: import, slot
"""

from .import_parser import ImportParser
from .slot_parser import SlotParser

__all__ = ['ImportParser', 'SlotParser']
