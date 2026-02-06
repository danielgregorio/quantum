"""
Quantum Plugin System

Provides extensible architecture for custom AST nodes, tags, adapters,
lifecycle hooks, and CLI commands.

Usage:
    from plugins import PluginLoader, PluginRegistry, HookManager

    # Load plugins from directory
    loader = PluginLoader()
    loader.discover_plugins('./plugins')

    # Access registry
    registry = loader.registry
    tag_handler = registry.get_tag_handler('my', 'custom-tag')
"""

from .manifest import PluginManifest, ManifestError
from .registry import PluginRegistry, PluginInfo
from .hooks import HookManager, HookType
from .loader import PluginLoader, PluginLoadError

__all__ = [
    'PluginManifest',
    'ManifestError',
    'PluginRegistry',
    'PluginInfo',
    'HookManager',
    'HookType',
    'PluginLoader',
    'PluginLoadError',
]
