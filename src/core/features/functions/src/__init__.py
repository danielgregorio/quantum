"""
Functions Feature (q:function)

Provides reusable functions with parameters, return values, caching, and REST API support.
"""

from .ast_node import FunctionNode, RestConfig
from .parser import parse_function, parse_function_param
from .runtime import FunctionRuntime, register_function, call_function, clear_cache

__all__ = [
    'FunctionNode', 'RestConfig',
    'parse_function', 'parse_function_param',
    'FunctionRuntime', 'register_function', 'call_function', 'clear_cache'
]
__version__ = '1.0.0'
