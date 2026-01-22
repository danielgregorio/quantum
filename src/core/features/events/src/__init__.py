"""
Event System for Quantum

Provides q:on (event handlers) and q:dispatch (event emission)
"""

from .ast_node import OnEventNode, DispatchEventNode
from .parser import parse_on_event, parse_dispatch_event
from .runtime import EventBus, EventHandler, get_event_bus, on, once, off, dispatch, clear

__all__ = [
    'OnEventNode', 'DispatchEventNode',
    'parse_on_event', 'parse_dispatch_event',
    'EventBus', 'EventHandler', 'get_event_bus',
    'on', 'once', 'off', 'dispatch', 'clear'
]
__version__ = "1.0.0"
