"""
Quantum Plugin Loader

Discovers and loads plugins from:
1. Local plugin directories
2. Installed Python packages (quantum-plugin-* naming convention)
3. Explicit plugin paths
"""

import sys
import importlib
import importlib.util
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import logging

from .manifest import PluginManifest, ManifestError
from .registry import PluginRegistry, PluginInfo, TagHandler, get_registry
from .hooks import HookManager, HookType, get_hook_manager

logger = logging.getLogger(__name__)


class PluginLoadError(Exception):
    """Error loading a plugin"""
    pass


class PluginLoader:
    """
    Discovers and loads Quantum plugins.

    Plugins can be loaded from:
    1. Local directories containing quantum-plugin.yaml
    2. Installed Python packages with quantum_plugin entry point
    3. Explicit paths to plugin directories

    Example usage:
        loader = PluginLoader()

        # Discover plugins in a directory
        loader.discover_plugins('./plugins')

        # Load a specific plugin
        loader.load_plugin('./plugins/my-plugin')

        # Access loaded plugins
        plugin = loader.registry.get_plugin('my-plugin')
    """

    MANIFEST_FILENAME = 'quantum-plugin.yaml'
    PACKAGE_PREFIX = 'quantum_plugin_'

    def __init__(
        self,
        registry: PluginRegistry = None,
        hook_manager: HookManager = None
    ):
        self.registry = registry or get_registry()
        self.hook_manager = hook_manager or get_hook_manager()
        self._loaded_paths: set = set()

    def discover_plugins(self, search_path: str) -> List[str]:
        """
        Discover and load all plugins in a directory.

        Args:
            search_path: Path to search for plugins

        Returns:
            List of loaded plugin names
        """
        search_dir = Path(search_path)
        if not search_dir.exists():
            logger.warning(f"Plugin search path does not exist: {search_path}")
            return []

        loaded = []
        for item in search_dir.iterdir():
            if item.is_dir():
                manifest_path = item / self.MANIFEST_FILENAME
                if manifest_path.exists():
                    try:
                        name = self.load_plugin(str(item))
                        loaded.append(name)
                    except PluginLoadError as e:
                        logger.error(f"Failed to load plugin {item.name}: {e}")

        logger.info(f"Discovered {len(loaded)} plugins in {search_path}")
        return loaded

    def discover_installed_plugins(self) -> List[str]:
        """
        Discover plugins installed as Python packages.

        Looks for packages with names starting with 'quantum_plugin_'
        or using the 'quantum.plugins' entry point group.

        Returns:
            List of loaded plugin names
        """
        loaded = []

        # Method 1: Look for quantum_plugin_* packages
        try:
            import pkgutil
            for importer, modname, ispkg in pkgutil.iter_modules():
                if modname.startswith(self.PACKAGE_PREFIX):
                    try:
                        name = self._load_installed_plugin(modname)
                        if name:
                            loaded.append(name)
                    except Exception as e:
                        logger.error(f"Failed to load installed plugin {modname}: {e}")
        except Exception as e:
            logger.debug(f"Error scanning for installed plugins: {e}")

        # Method 2: Use entry points (Python 3.9+)
        try:
            from importlib.metadata import entry_points
            eps = entry_points()

            # Handle different Python versions
            if hasattr(eps, 'select'):
                # Python 3.10+
                quantum_plugins = eps.select(group='quantum.plugins')
            else:
                # Python 3.9
                quantum_plugins = eps.get('quantum.plugins', [])

            for ep in quantum_plugins:
                try:
                    plugin_module = ep.load()
                    if hasattr(plugin_module, 'get_manifest'):
                        manifest_data = plugin_module.get_manifest()
                        manifest = PluginManifest.from_dict(manifest_data)
                        self._register_plugin_from_module(manifest, plugin_module)
                        loaded.append(manifest.name)
                except Exception as e:
                    logger.error(f"Failed to load entry point {ep.name}: {e}")
        except ImportError:
            pass  # importlib.metadata not available

        logger.info(f"Discovered {len(loaded)} installed plugins")
        return loaded

    def load_plugin(self, plugin_path: str) -> str:
        """
        Load a plugin from a directory.

        Args:
            plugin_path: Path to plugin directory

        Returns:
            Loaded plugin name

        Raises:
            PluginLoadError: If plugin cannot be loaded
        """
        plugin_dir = Path(plugin_path).resolve()

        # Check if already loaded
        if str(plugin_dir) in self._loaded_paths:
            logger.debug(f"Plugin already loaded: {plugin_dir}")
            manifest = PluginManifest.from_file(plugin_dir / self.MANIFEST_FILENAME)
            return manifest.name

        # Find and parse manifest
        manifest_path = plugin_dir / self.MANIFEST_FILENAME
        if not manifest_path.exists():
            raise PluginLoadError(f"Manifest not found: {manifest_path}")

        try:
            manifest = PluginManifest.from_file(manifest_path)
        except ManifestError as e:
            raise PluginLoadError(f"Invalid manifest: {e}")

        # Validate manifest
        errors = manifest.validate()
        if errors:
            raise PluginLoadError(f"Manifest validation failed: {errors}")

        # Create plugin info
        info = PluginInfo(
            name=manifest.name,
            version=manifest.version,
            manifest=manifest,
            source_path=plugin_dir
        )

        # Add plugin directory to Python path
        plugin_src = plugin_dir / 'src'
        if plugin_src.exists():
            sys.path.insert(0, str(plugin_src))
        sys.path.insert(0, str(plugin_dir))

        try:
            # Load components
            self._load_tag_handlers(manifest, info, plugin_dir)
            self._load_node_classes(manifest, info, plugin_dir)
            self._load_adapters(manifest, info, plugin_dir)
            self._load_cli_commands(manifest, info, plugin_dir)
            self._load_hooks(manifest, info, plugin_dir)

            # Register plugin
            self.registry.register_plugin(info)
            self._loaded_paths.add(str(plugin_dir))

            # Execute on_init hooks
            from .hooks import HookContext
            ctx = HookContext(
                hook_type=HookType.ON_INIT,
                data={'plugin': info}
            )
            self.hook_manager.execute(HookType.ON_INIT, ctx)

            logger.info(f"Loaded plugin: {manifest.name}@{manifest.version}")
            return manifest.name

        except Exception as e:
            # Clean up on failure
            if str(plugin_src) in sys.path:
                sys.path.remove(str(plugin_src))
            if str(plugin_dir) in sys.path:
                sys.path.remove(str(plugin_dir))
            raise PluginLoadError(f"Failed to load plugin components: {e}")

    def unload_plugin(self, name: str) -> bool:
        """
        Unload a plugin.

        Args:
            name: Plugin name

        Returns:
            True if plugin was unloaded
        """
        info = self.registry.get_plugin(name)
        if not info:
            return False

        # Execute on_shutdown hooks for this plugin
        from .hooks import HookContext
        ctx = HookContext(
            hook_type=HookType.ON_SHUTDOWN,
            data={'plugin': info}
        )
        self.hook_manager.execute(HookType.ON_SHUTDOWN, ctx)

        # Unregister hooks
        self.hook_manager.unregister_all(name)

        # Unregister from registry
        self.registry.unregister_plugin(name)

        # Remove from loaded paths
        if info.source_path:
            path_str = str(info.source_path)
            if path_str in self._loaded_paths:
                self._loaded_paths.remove(path_str)

        logger.info(f"Unloaded plugin: {name}")
        return True

    def reload_plugin(self, name: str) -> str:
        """
        Reload a plugin (unload and load again).

        Args:
            name: Plugin name

        Returns:
            Plugin name

        Raises:
            PluginLoadError: If plugin cannot be reloaded
        """
        info = self.registry.get_plugin(name)
        if not info:
            raise PluginLoadError(f"Plugin not found: {name}")

        source_path = str(info.source_path)
        self.unload_plugin(name)
        return self.load_plugin(source_path)

    def _load_installed_plugin(self, module_name: str) -> Optional[str]:
        """Load a plugin from an installed package"""
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, 'get_manifest'):
                manifest_data = module.get_manifest()
                manifest = PluginManifest.from_dict(manifest_data)
                self._register_plugin_from_module(manifest, module)
                return manifest.name
        except Exception as e:
            logger.error(f"Error loading installed plugin {module_name}: {e}")
        return None

    def _register_plugin_from_module(self, manifest: PluginManifest, module: Any) -> None:
        """Register a plugin loaded from a Python module"""
        info = PluginInfo(
            name=manifest.name,
            version=manifest.version,
            manifest=manifest,
            source_path=Path(module.__file__).parent if hasattr(module, '__file__') else Path('.')
        )
        self.registry.register_plugin(info)

    def _load_module_from_handler(self, handler_str: str, plugin_dir: Path) -> tuple:
        """
        Load a module and get the specified object.

        Args:
            handler_str: Handler string in format "module.path:ClassName"
            plugin_dir: Plugin directory

        Returns:
            Tuple of (module, object)
        """
        if ':' not in handler_str:
            raise PluginLoadError(f"Invalid handler format: {handler_str}. Expected 'module:Class'")

        module_path, obj_name = handler_str.rsplit(':', 1)

        # Try to import the module
        try:
            module = importlib.import_module(module_path)
        except ImportError:
            # Try as relative path from plugin dir
            try:
                module_file = plugin_dir / (module_path.replace('.', '/') + '.py')
                if not module_file.exists():
                    module_file = plugin_dir / 'src' / (module_path.replace('.', '/') + '.py')

                if not module_file.exists():
                    raise PluginLoadError(f"Module not found: {module_path}")

                spec = importlib.util.spec_from_file_location(module_path, module_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception as e:
                raise PluginLoadError(f"Failed to import module {module_path}: {e}")

        # Get the object
        if not hasattr(module, obj_name):
            raise PluginLoadError(f"Object not found in module: {obj_name}")

        return module, getattr(module, obj_name)

    def _load_tag_handlers(self, manifest: PluginManifest, info: PluginInfo, plugin_dir: Path) -> None:
        """Load tag handlers from manifest"""
        for tag_def in manifest.tags:
            try:
                module, handler_class = self._load_module_from_handler(tag_def.handler, plugin_dir)

                # Instantiate handler
                if isinstance(handler_class, type):
                    handler = handler_class()
                else:
                    handler = handler_class

                # Set prefix if not set
                if hasattr(handler, 'prefix') and not handler.prefix:
                    handler.prefix = tag_def.prefix

                # Register
                self.registry.register_tag_handler(tag_def.prefix, handler, manifest.name)
                info.tag_handlers[tag_def.prefix] = handler
                info.loaded_modules[tag_def.handler] = module

                logger.debug(f"Loaded tag handler: {tag_def.prefix}:* from {tag_def.handler}")

            except Exception as e:
                logger.error(f"Failed to load tag handler {tag_def.prefix}: {e}")
                raise

    def _load_node_classes(self, manifest: PluginManifest, info: PluginInfo, plugin_dir: Path) -> None:
        """Load AST node classes from manifest"""
        for node_def in manifest.nodes:
            try:
                module, node_class = self._load_module_from_handler(node_def.handler, plugin_dir)

                self.registry.register_node_class(node_def.name, node_class, manifest.name)
                info.node_classes[node_def.name] = node_class
                info.loaded_modules[node_def.handler] = module

                logger.debug(f"Loaded node class: {node_def.name}")

            except Exception as e:
                logger.error(f"Failed to load node class {node_def.name}: {e}")
                raise

    def _load_adapters(self, manifest: PluginManifest, info: PluginInfo, plugin_dir: Path) -> None:
        """Load adapters from manifest"""
        for adapter_def in manifest.adapters:
            try:
                module, adapter_class = self._load_module_from_handler(adapter_def.handler, plugin_dir)

                # Instantiate if class
                if isinstance(adapter_class, type):
                    adapter = adapter_class()
                else:
                    adapter = adapter_class

                self.registry.register_adapter(adapter_def.name, adapter, manifest.name)
                info.adapters[adapter_def.name] = adapter
                info.loaded_modules[adapter_def.handler] = module

                logger.debug(f"Loaded adapter: {adapter_def.name}")

            except Exception as e:
                logger.error(f"Failed to load adapter {adapter_def.name}: {e}")
                raise

    def _load_cli_commands(self, manifest: PluginManifest, info: PluginInfo, plugin_dir: Path) -> None:
        """Load CLI commands from manifest"""
        for cmd_def in manifest.cli_commands:
            try:
                module, handler = self._load_module_from_handler(cmd_def.handler, plugin_dir)

                self.registry.register_cli_command(
                    cmd_def.name,
                    handler,
                    manifest.name,
                    cmd_def.aliases
                )
                info.cli_commands[cmd_def.name] = handler
                info.loaded_modules[cmd_def.handler] = module

                logger.debug(f"Loaded CLI command: {cmd_def.name}")

            except Exception as e:
                logger.error(f"Failed to load CLI command {cmd_def.name}: {e}")
                raise

    def _load_hooks(self, manifest: PluginManifest, info: PluginInfo, plugin_dir: Path) -> None:
        """Load lifecycle hooks from manifest"""
        for hook_def in manifest.hooks:
            try:
                module, handler = self._load_module_from_handler(hook_def.handler, plugin_dir)

                # Convert string to HookType
                hook_type = HookType(hook_def.hook_type)

                self.hook_manager.register(
                    hook_type,
                    handler,
                    manifest.name,
                    hook_def.priority
                )
                info.loaded_modules[hook_def.handler] = module

                logger.debug(f"Loaded hook: {hook_def.hook_type} from {hook_def.handler}")

            except Exception as e:
                logger.error(f"Failed to load hook {hook_def.hook_type}: {e}")
                raise

    def get_loaded_plugins(self) -> List[str]:
        """Get names of all loaded plugins"""
        return list(self.registry.get_all_plugins().keys())


# Global loader instance
_global_loader: Optional[PluginLoader] = None


def get_loader() -> PluginLoader:
    """Get the global plugin loader instance"""
    global _global_loader
    if _global_loader is None:
        _global_loader = PluginLoader()
    return _global_loader


def set_loader(loader: PluginLoader) -> None:
    """Set the global plugin loader instance"""
    global _global_loader
    _global_loader = loader
