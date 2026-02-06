"""
Quantum Plugin Registry

Central registry for all loaded plugins and their components.
Provides lookup and management for tags, nodes, adapters, and CLI commands.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Type, Callable
from pathlib import Path
import logging

from .manifest import PluginManifest, TagDefinition, ASTNodeDefinition

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """Information about a loaded plugin"""
    name: str
    version: str
    manifest: PluginManifest
    source_path: Path
    enabled: bool = True
    loaded_modules: Dict[str, Any] = field(default_factory=dict)

    # Loaded components
    tag_handlers: Dict[str, Any] = field(default_factory=dict)     # prefix -> handler
    node_classes: Dict[str, Type] = field(default_factory=dict)    # name -> class
    adapters: Dict[str, Any] = field(default_factory=dict)         # name -> adapter
    cli_commands: Dict[str, Callable] = field(default_factory=dict)  # name -> function

    def __repr__(self):
        status = "enabled" if self.enabled else "disabled"
        return f"<PluginInfo {self.name}@{self.version} ({status})>"


class TagHandler:
    """
    Base class for custom tag handlers.

    Plugins should extend this class to handle custom tags.

    Example:
        class MyTagHandler(TagHandler):
            prefix = "my"

            def parse(self, element, parser):
                # Parse XML element into AST node
                return MyCustomNode(...)

            def execute(self, node, context, runtime):
                # Execute the node
                return result

            def render(self, node, renderer):
                # Render node to HTML
                return "<div>...</div>"
    """

    prefix: str = ""  # Tag prefix, e.g., "my" for <my:tag>

    def parse(self, element: Any, parser: Any) -> Any:
        """
        Parse XML element into AST node.

        Args:
            element: XML element (ElementTree Element)
            parser: Quantum parser instance

        Returns:
            AST node
        """
        raise NotImplementedError("Tag handler must implement parse()")

    def execute(self, node: Any, context: Any, runtime: Any) -> Any:
        """
        Execute the AST node.

        Args:
            node: AST node to execute
            context: Execution context
            runtime: Component runtime

        Returns:
            Execution result
        """
        return None

    def render(self, node: Any, renderer: Any) -> str:
        """
        Render AST node to HTML.

        Args:
            node: AST node to render
            renderer: Renderer instance

        Returns:
            HTML string
        """
        return ""

    def get_supported_tags(self) -> List[str]:
        """
        Get list of supported tag names (without prefix).

        Returns:
            List of tag names, empty list means all tags with this prefix
        """
        return []


class PluginRegistry:
    """
    Central registry for all plugin components.

    Provides lookup and management for:
    - Plugin manifests and info
    - Tag handlers by prefix
    - AST node classes
    - Adapters
    - CLI commands
    """

    def __init__(self):
        self._plugins: Dict[str, PluginInfo] = {}
        self._tag_handlers: Dict[str, TagHandler] = {}  # prefix -> handler
        self._node_classes: Dict[str, Type] = {}        # name -> class
        self._adapters: Dict[str, Any] = {}             # name -> adapter
        self._cli_commands: Dict[str, Callable] = {}    # name -> function
        self._tag_prefixes: Dict[str, str] = {}         # prefix -> plugin_name

    def register_plugin(self, info: PluginInfo) -> None:
        """
        Register a loaded plugin.

        Args:
            info: Plugin information
        """
        if info.name in self._plugins:
            logger.warning(f"Plugin '{info.name}' already registered, replacing")

        self._plugins[info.name] = info
        logger.info(f"Registered plugin: {info.name}@{info.version}")

    def unregister_plugin(self, name: str) -> bool:
        """
        Unregister a plugin and remove all its components.

        Args:
            name: Plugin name

        Returns:
            True if plugin was found and removed
        """
        if name not in self._plugins:
            return False

        info = self._plugins[name]

        # Remove tag handlers
        for prefix in info.tag_handlers:
            if prefix in self._tag_handlers:
                del self._tag_handlers[prefix]
            if prefix in self._tag_prefixes:
                del self._tag_prefixes[prefix]

        # Remove node classes
        for node_name in info.node_classes:
            if node_name in self._node_classes:
                del self._node_classes[node_name]

        # Remove adapters
        for adapter_name in info.adapters:
            if adapter_name in self._adapters:
                del self._adapters[adapter_name]

        # Remove CLI commands
        for cmd_name in info.cli_commands:
            if cmd_name in self._cli_commands:
                del self._cli_commands[cmd_name]

        del self._plugins[name]
        logger.info(f"Unregistered plugin: {name}")
        return True

    def get_plugin(self, name: str) -> Optional[PluginInfo]:
        """Get plugin info by name"""
        return self._plugins.get(name)

    def get_all_plugins(self) -> Dict[str, PluginInfo]:
        """Get all registered plugins"""
        return self._plugins

    def get_enabled_plugins(self) -> Dict[str, PluginInfo]:
        """Get only enabled plugins"""
        return {k: v for k, v in self._plugins.items() if v.enabled}

    # Tag Handler Management
    def register_tag_handler(self, prefix: str, handler: TagHandler, plugin_name: str) -> None:
        """
        Register a tag handler for a prefix.

        Args:
            prefix: Tag prefix (e.g., "my" for <my:tag>)
            handler: Tag handler instance
            plugin_name: Name of the plugin providing this handler
        """
        if prefix in self._tag_handlers:
            logger.warning(f"Tag prefix '{prefix}' already registered by {self._tag_prefixes.get(prefix)}")

        self._tag_handlers[prefix] = handler
        self._tag_prefixes[prefix] = plugin_name

        # Also add to plugin info
        if plugin_name in self._plugins:
            self._plugins[plugin_name].tag_handlers[prefix] = handler

        logger.debug(f"Registered tag handler: {prefix}:* from {plugin_name}")

    def get_tag_handler(self, prefix: str) -> Optional[TagHandler]:
        """Get tag handler for a prefix"""
        return self._tag_handlers.get(prefix)

    def has_tag_prefix(self, prefix: str) -> bool:
        """Check if a tag prefix is registered"""
        return prefix in self._tag_handlers

    def get_all_tag_prefixes(self) -> List[str]:
        """Get all registered tag prefixes"""
        return list(self._tag_handlers.keys())

    # AST Node Management
    def register_node_class(self, name: str, node_class: Type, plugin_name: str) -> None:
        """
        Register a custom AST node class.

        Args:
            name: Node class name
            node_class: Node class type
            plugin_name: Name of the plugin providing this node
        """
        self._node_classes[name] = node_class

        if plugin_name in self._plugins:
            self._plugins[plugin_name].node_classes[name] = node_class

        logger.debug(f"Registered node class: {name} from {plugin_name}")

    def get_node_class(self, name: str) -> Optional[Type]:
        """Get AST node class by name"""
        return self._node_classes.get(name)

    def get_all_node_classes(self) -> Dict[str, Type]:
        """Get all registered node classes"""
        return self._node_classes

    # Adapter Management
    def register_adapter(self, name: str, adapter: Any, plugin_name: str) -> None:
        """
        Register a custom adapter.

        Args:
            name: Adapter name
            adapter: Adapter instance or class
            plugin_name: Name of the plugin providing this adapter
        """
        self._adapters[name] = adapter

        if plugin_name in self._plugins:
            self._plugins[plugin_name].adapters[name] = adapter

        logger.debug(f"Registered adapter: {name} from {plugin_name}")

    def get_adapter(self, name: str) -> Optional[Any]:
        """Get adapter by name"""
        return self._adapters.get(name)

    def get_all_adapters(self) -> Dict[str, Any]:
        """Get all registered adapters"""
        return self._adapters

    # CLI Command Management
    def register_cli_command(
        self,
        name: str,
        handler: Callable,
        plugin_name: str,
        aliases: List[str] = None
    ) -> None:
        """
        Register a CLI command.

        Args:
            name: Command name
            handler: Command handler function
            plugin_name: Name of the plugin providing this command
            aliases: Optional command aliases
        """
        self._cli_commands[name] = handler

        # Register aliases
        for alias in (aliases or []):
            self._cli_commands[alias] = handler

        if plugin_name in self._plugins:
            self._plugins[plugin_name].cli_commands[name] = handler

        logger.debug(f"Registered CLI command: {name} from {plugin_name}")

    def get_cli_command(self, name: str) -> Optional[Callable]:
        """Get CLI command by name"""
        return self._cli_commands.get(name)

    def get_all_cli_commands(self) -> Dict[str, Callable]:
        """Get all registered CLI commands"""
        return self._cli_commands

    # Utility methods
    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin"""
        if name in self._plugins:
            self._plugins[name].enabled = True
            return True
        return False

    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin"""
        if name in self._plugins:
            self._plugins[name].enabled = False
            return True
        return False

    def clear(self) -> None:
        """Clear all registered components"""
        self._plugins.clear()
        self._tag_handlers.clear()
        self._node_classes.clear()
        self._adapters.clear()
        self._cli_commands.clear()
        self._tag_prefixes.clear()

    def get_stats(self) -> Dict[str, int]:
        """Get registry statistics"""
        return {
            'plugins': len(self._plugins),
            'enabled_plugins': len(self.get_enabled_plugins()),
            'tag_handlers': len(self._tag_handlers),
            'node_classes': len(self._node_classes),
            'adapters': len(self._adapters),
            'cli_commands': len(self._cli_commands)
        }


# Global registry instance
_global_registry: Optional[PluginRegistry] = None


def get_registry() -> PluginRegistry:
    """Get the global plugin registry instance"""
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry


def set_registry(registry: PluginRegistry) -> None:
    """Set the global plugin registry instance"""
    global _global_registry
    _global_registry = registry
