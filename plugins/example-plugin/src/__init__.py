"""
Example Plugin for Quantum Framework

Demonstrates:
- Custom tag handlers
- Custom AST nodes
- Lifecycle hooks
- CLI commands
"""

from .nodes import HelloNode, CounterNode, TimestampNode
from .tags import ExampleTagHandler
from .hooks import on_before_parse, on_after_render, on_plugin_init
from .cli import greet_command, plugin_info_command

__all__ = [
    'HelloNode',
    'CounterNode',
    'TimestampNode',
    'ExampleTagHandler',
    'on_before_parse',
    'on_after_render',
    'on_plugin_init',
    'greet_command',
    'plugin_info_command',
]
