"""
Tests for Quantum Plugin System

Tests:
- Plugin manifest parsing
- Plugin registry operations
- Plugin hook system
- Plugin loading
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from plugins.manifest import (
    PluginManifest,
    ManifestError,
    TagDefinition,
    HookDefinition,
    AdapterDefinition,
    CLICommandDefinition,
    ASTNodeDefinition,
)
from plugins.registry import (
    PluginRegistry,
    PluginInfo,
    TagHandler,
    get_registry,
    set_registry,
)
from plugins.hooks import (
    HookManager,
    HookType,
    HookContext,
    HookRegistration,
    get_hook_manager,
    set_hook_manager,
)
from plugins.loader import (
    PluginLoader,
    PluginLoadError,
    get_loader,
)


# ============================================
# Tag Definition Tests
# ============================================

class TestTagDefinition:
    """Test TagDefinition dataclass."""

    def test_valid_tag_definition(self):
        """Test creating a valid tag definition."""
        tag = TagDefinition(prefix="my", handler="src.tags:MyHandler")
        assert tag.prefix == "my"
        assert tag.handler == "src.tags:MyHandler"
        assert tag.tags == []

    def test_tag_definition_with_tags(self):
        """Test tag definition with specific tags."""
        tag = TagDefinition(prefix="my", handler="src.tags:MyHandler", tags=["custom", "special"])
        assert tag.tags == ["custom", "special"]

    def test_tag_definition_missing_prefix(self):
        """Test tag definition requires prefix."""
        with pytest.raises(ManifestError, match="prefix"):
            TagDefinition(prefix="", handler="src:Handler")

    def test_tag_definition_missing_handler(self):
        """Test tag definition requires handler."""
        with pytest.raises(ManifestError, match="handler"):
            TagDefinition(prefix="my", handler="")


# ============================================
# Hook Definition Tests
# ============================================

class TestHookDefinition:
    """Test HookDefinition dataclass."""

    def test_valid_hook_definition(self):
        """Test creating valid hook definitions."""
        valid_hooks = [
            'before_parse', 'after_parse',
            'before_render', 'after_render',
            'before_execute', 'after_execute',
            'on_error', 'on_init', 'on_shutdown'
        ]
        for hook_type in valid_hooks:
            hook = HookDefinition(hook_type=hook_type, handler="src.hooks:handler")
            assert hook.hook_type == hook_type
            assert hook.priority == 100

    def test_hook_definition_with_priority(self):
        """Test hook definition with custom priority."""
        hook = HookDefinition(hook_type="before_render", handler="src:fn", priority=50)
        assert hook.priority == 50

    def test_hook_definition_invalid_type(self):
        """Test hook definition rejects invalid type."""
        with pytest.raises(ManifestError, match="Invalid hook type"):
            HookDefinition(hook_type="invalid_hook", handler="src:fn")


# ============================================
# Plugin Manifest Tests
# ============================================

class TestPluginManifest:
    """Test PluginManifest parsing and validation."""

    def test_manifest_from_dict_minimal(self):
        """Test manifest from minimal dictionary."""
        data = {
            'name': 'my-plugin',
            'version': '1.0.0'
        }
        manifest = PluginManifest.from_dict(data)
        assert manifest.name == 'my-plugin'
        assert manifest.version == '1.0.0'
        assert manifest.tags == []
        assert manifest.hooks == []

    def test_manifest_from_dict_full(self):
        """Test manifest with all fields."""
        data = {
            'name': 'full-plugin',
            'version': '2.0.0',
            'description': 'A full plugin',
            'author': 'Test Author',
            'license': 'MIT',
            'quantum': '>=1.0.0',
            'tags': [
                {'prefix': 'my', 'handler': 'src.tags:Handler', 'tags': ['tag1']}
            ],
            'hooks': [
                {'hook_type': 'before_render', 'handler': 'src.hooks:fn', 'priority': 50}
            ],
            'adapters': [
                {'name': 'my-adapter', 'handler': 'src.adapters:Adapter', 'target': 'html'}
            ],
            'cli': [
                {'name': 'my-cmd', 'handler': 'src.cli:cmd', 'help': 'My command', 'aliases': ['mc']}
            ],
            'nodes': [
                {'name': 'MyNode', 'handler': 'src.nodes:MyNode', 'base': 'QuantumNode'}
            ],
            'dependencies': ['other-plugin>=1.0.0']
        }
        manifest = PluginManifest.from_dict(data)

        assert manifest.name == 'full-plugin'
        assert manifest.version == '2.0.0'
        assert manifest.description == 'A full plugin'
        assert manifest.author == 'Test Author'
        assert len(manifest.tags) == 1
        assert len(manifest.hooks) == 1
        assert len(manifest.adapters) == 1
        assert len(manifest.cli_commands) == 1
        assert len(manifest.nodes) == 1
        assert 'other-plugin>=1.0.0' in manifest.dependencies

    def test_manifest_missing_name(self):
        """Test manifest requires name."""
        data = {'version': '1.0.0'}
        with pytest.raises(ManifestError, match="name"):
            PluginManifest.from_dict(data)

    def test_manifest_missing_version(self):
        """Test manifest requires version."""
        data = {'name': 'my-plugin'}
        with pytest.raises(ManifestError, match="version"):
            PluginManifest.from_dict(data)

    def test_manifest_validate_valid(self):
        """Test validate returns empty for valid manifest."""
        manifest = PluginManifest(name='valid-plugin', version='1.0.0')
        errors = manifest.validate()
        assert errors == []

    def test_manifest_validate_invalid_name(self):
        """Test validate catches invalid name."""
        manifest = PluginManifest(name='Invalid Plugin!', version='1.0.0')
        errors = manifest.validate()
        assert any('Invalid plugin name' in e for e in errors)

    def test_manifest_to_dict(self):
        """Test manifest serialization to dict."""
        manifest = PluginManifest(
            name='test',
            version='1.0.0',
            description='Test plugin'
        )
        d = manifest.to_dict()
        assert d['name'] == 'test'
        assert d['version'] == '1.0.0'
        assert d['description'] == 'Test plugin'

    def test_manifest_from_file(self, tmp_path):
        """Test loading manifest from file."""
        manifest_content = """
name: file-plugin
version: 1.2.3
description: From file
"""
        manifest_file = tmp_path / 'quantum-plugin.yaml'
        manifest_file.write_text(manifest_content)

        manifest = PluginManifest.from_file(manifest_file)
        assert manifest.name == 'file-plugin'
        assert manifest.version == '1.2.3'

    def test_manifest_from_file_not_found(self):
        """Test loading manifest from non-existent file."""
        with pytest.raises(ManifestError, match="not found"):
            PluginManifest.from_file('/nonexistent/manifest.yaml')


# ============================================
# Plugin Registry Tests
# ============================================

class TestPluginRegistry:
    """Test PluginRegistry operations."""

    @pytest.fixture
    def registry(self):
        """Fresh registry for each test."""
        return PluginRegistry()

    @pytest.fixture
    def sample_plugin_info(self):
        """Sample plugin info."""
        manifest = PluginManifest(name='test-plugin', version='1.0.0')
        return PluginInfo(
            name='test-plugin',
            version='1.0.0',
            manifest=manifest,
            source_path=Path('/test'),
        )

    def test_register_plugin(self, registry, sample_plugin_info):
        """Test registering a plugin."""
        registry.register_plugin(sample_plugin_info)
        assert registry.get_plugin('test-plugin') is not None
        assert registry.get_plugin('test-plugin').version == '1.0.0'

    def test_unregister_plugin(self, registry, sample_plugin_info):
        """Test unregistering a plugin."""
        registry.register_plugin(sample_plugin_info)
        result = registry.unregister_plugin('test-plugin')
        assert result is True
        assert registry.get_plugin('test-plugin') is None

    def test_unregister_nonexistent(self, registry):
        """Test unregistering non-existent plugin."""
        result = registry.unregister_plugin('nonexistent')
        assert result is False

    def test_get_all_plugins(self, registry, sample_plugin_info):
        """Test getting all plugins."""
        registry.register_plugin(sample_plugin_info)
        plugins = registry.get_all_plugins()
        assert 'test-plugin' in plugins

    def test_get_enabled_plugins(self, registry, sample_plugin_info):
        """Test getting only enabled plugins."""
        registry.register_plugin(sample_plugin_info)
        registry.disable_plugin('test-plugin')

        all_plugins = registry.get_all_plugins()
        enabled = registry.get_enabled_plugins()

        assert 'test-plugin' in all_plugins
        assert 'test-plugin' not in enabled

    def test_register_tag_handler(self, registry, sample_plugin_info):
        """Test registering a tag handler."""
        registry.register_plugin(sample_plugin_info)

        class TestHandler(TagHandler):
            prefix = "test"

        handler = TestHandler()
        registry.register_tag_handler('test', handler, 'test-plugin')

        assert registry.get_tag_handler('test') is handler
        assert registry.has_tag_prefix('test')

    def test_register_node_class(self, registry, sample_plugin_info):
        """Test registering an AST node class."""
        registry.register_plugin(sample_plugin_info)

        class TestNode:
            pass

        registry.register_node_class('TestNode', TestNode, 'test-plugin')
        assert registry.get_node_class('TestNode') is TestNode

    def test_register_adapter(self, registry, sample_plugin_info):
        """Test registering an adapter."""
        registry.register_plugin(sample_plugin_info)

        class TestAdapter:
            pass

        adapter = TestAdapter()
        registry.register_adapter('test-adapter', adapter, 'test-plugin')
        assert registry.get_adapter('test-adapter') is adapter

    def test_register_cli_command(self, registry, sample_plugin_info):
        """Test registering a CLI command."""
        registry.register_plugin(sample_plugin_info)

        def test_cmd():
            pass

        registry.register_cli_command('test-cmd', test_cmd, 'test-plugin', aliases=['tc'])
        assert registry.get_cli_command('test-cmd') is test_cmd
        assert registry.get_cli_command('tc') is test_cmd

    def test_enable_disable_plugin(self, registry, sample_plugin_info):
        """Test enabling and disabling plugins."""
        registry.register_plugin(sample_plugin_info)

        assert registry.get_plugin('test-plugin').enabled is True

        registry.disable_plugin('test-plugin')
        assert registry.get_plugin('test-plugin').enabled is False

        registry.enable_plugin('test-plugin')
        assert registry.get_plugin('test-plugin').enabled is True

    def test_clear_registry(self, registry, sample_plugin_info):
        """Test clearing the registry."""
        registry.register_plugin(sample_plugin_info)
        registry.clear()

        assert registry.get_all_plugins() == {}
        assert registry.get_all_tag_prefixes() == []

    def test_get_stats(self, registry, sample_plugin_info):
        """Test getting registry statistics."""
        registry.register_plugin(sample_plugin_info)
        stats = registry.get_stats()

        assert 'plugins' in stats
        assert 'enabled_plugins' in stats
        assert stats['plugins'] == 1


# ============================================
# Hook Manager Tests
# ============================================

class TestHookManager:
    """Test HookManager operations."""

    @pytest.fixture
    def hook_manager(self):
        """Fresh hook manager for each test."""
        return HookManager()

    def test_register_hook(self, hook_manager):
        """Test registering a hook."""
        callback = MagicMock()
        hook_manager.register(HookType.BEFORE_PARSE, callback, 'test-plugin')

        hooks = hook_manager.get_hooks(HookType.BEFORE_PARSE)
        assert len(hooks) == 1
        assert hooks[0].callback is callback

    def test_register_hook_with_priority(self, hook_manager):
        """Test hooks are sorted by priority."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        callback3 = MagicMock()

        hook_manager.register(HookType.BEFORE_RENDER, callback1, 'plugin1', priority=100)
        hook_manager.register(HookType.BEFORE_RENDER, callback2, 'plugin2', priority=50)
        hook_manager.register(HookType.BEFORE_RENDER, callback3, 'plugin3', priority=150)

        hooks = hook_manager.get_hooks(HookType.BEFORE_RENDER)
        assert hooks[0].priority == 50
        assert hooks[1].priority == 100
        assert hooks[2].priority == 150

    def test_unregister_hook(self, hook_manager):
        """Test unregistering hooks."""
        callback = MagicMock()
        hook_manager.register(HookType.AFTER_PARSE, callback, 'test-plugin')

        removed = hook_manager.unregister(HookType.AFTER_PARSE, 'test-plugin')
        assert removed == 1
        assert len(hook_manager.get_hooks(HookType.AFTER_PARSE)) == 0

    def test_unregister_all(self, hook_manager):
        """Test unregistering all hooks for a plugin."""
        callback = MagicMock()
        hook_manager.register(HookType.BEFORE_PARSE, callback, 'test-plugin')
        hook_manager.register(HookType.AFTER_PARSE, callback, 'test-plugin')
        hook_manager.register(HookType.BEFORE_RENDER, callback, 'test-plugin')

        removed = hook_manager.unregister_all('test-plugin')
        assert removed == 3

    def test_execute_hooks(self, hook_manager):
        """Test executing hooks."""
        callback = MagicMock()
        hook_manager.register(HookType.BEFORE_RENDER, callback, 'test-plugin')

        ctx = HookContext(hook_type=HookType.BEFORE_RENDER)
        hook_manager.execute(HookType.BEFORE_RENDER, ctx)

        callback.assert_called_once()

    def test_execute_hooks_in_order(self, hook_manager):
        """Test hooks execute in priority order."""
        call_order = []

        def callback1(ctx):
            call_order.append(1)

        def callback2(ctx):
            call_order.append(2)

        hook_manager.register(HookType.AFTER_EXECUTE, callback1, 'plugin1', priority=100)
        hook_manager.register(HookType.AFTER_EXECUTE, callback2, 'plugin2', priority=50)

        ctx = HookContext(hook_type=HookType.AFTER_EXECUTE)
        hook_manager.execute(HookType.AFTER_EXECUTE, ctx)

        assert call_order == [2, 1]  # Lower priority first

    def test_hook_context_skip(self, hook_manager):
        """Test skipping remaining hooks."""
        callback1 = MagicMock()
        callback2 = MagicMock()

        def skip_hook(ctx):
            ctx.skip_remaining()

        hook_manager.register(HookType.BEFORE_PARSE, skip_hook, 'plugin1', priority=50)
        hook_manager.register(HookType.BEFORE_PARSE, callback2, 'plugin2', priority=100)

        ctx = HookContext(hook_type=HookType.BEFORE_PARSE)
        hook_manager.execute(HookType.BEFORE_PARSE, ctx)

        callback2.assert_not_called()

    def test_hook_context_modification(self, hook_manager):
        """Test modifying context in hooks."""
        def modify_source(ctx):
            ctx.set_ast({'modified': True})

        hook_manager.register(HookType.AFTER_PARSE, modify_source, 'test-plugin')

        result = hook_manager.execute_after_parse({'original': True})
        assert result == {'modified': True}

    def test_enable_disable_hooks(self, hook_manager):
        """Test enabling/disabling hook execution."""
        callback = MagicMock()
        hook_manager.register(HookType.BEFORE_RENDER, callback, 'test-plugin')

        hook_manager.disable()
        ctx = HookContext(hook_type=HookType.BEFORE_RENDER)
        hook_manager.execute(HookType.BEFORE_RENDER, ctx)
        callback.assert_not_called()

        hook_manager.enable()
        hook_manager.execute(HookType.BEFORE_RENDER, ctx)
        callback.assert_called_once()

    def test_hook_count(self, hook_manager):
        """Test counting hooks."""
        callback = MagicMock()
        hook_manager.register(HookType.BEFORE_PARSE, callback, 'plugin1')
        hook_manager.register(HookType.AFTER_PARSE, callback, 'plugin1')
        hook_manager.register(HookType.BEFORE_PARSE, callback, 'plugin2')

        assert hook_manager.count(HookType.BEFORE_PARSE) == 2
        assert hook_manager.count(HookType.AFTER_PARSE) == 1
        assert hook_manager.count() == 3

    def test_clear_hooks(self, hook_manager):
        """Test clearing all hooks."""
        callback = MagicMock()
        hook_manager.register(HookType.BEFORE_PARSE, callback, 'test-plugin')
        hook_manager.clear()

        assert hook_manager.count() == 0


# ============================================
# Hook Context Tests
# ============================================

class TestHookContext:
    """Test HookContext functionality."""

    def test_context_creation(self):
        """Test creating a hook context."""
        ctx = HookContext(hook_type=HookType.BEFORE_PARSE)
        assert ctx.hook_type == HookType.BEFORE_PARSE
        assert ctx.skip is False
        assert ctx.modified is False

    def test_context_set_result(self):
        """Test setting result in context."""
        ctx = HookContext(hook_type=HookType.AFTER_EXECUTE)
        ctx.set_result({'data': 'value'})

        assert ctx.result == {'data': 'value'}
        assert ctx.modified is True

    def test_context_set_html(self):
        """Test setting HTML in context."""
        ctx = HookContext(hook_type=HookType.AFTER_RENDER)
        ctx.set_html('<div>Modified</div>')

        assert ctx.html == '<div>Modified</div>'
        assert ctx.modified is True

    def test_context_set_ast(self):
        """Test setting AST in context."""
        ctx = HookContext(hook_type=HookType.AFTER_PARSE)
        ctx.set_ast({'node': 'value'})

        assert ctx.ast == {'node': 'value'}
        assert ctx.modified is True

    def test_context_skip_remaining(self):
        """Test skip remaining flag."""
        ctx = HookContext(hook_type=HookType.BEFORE_RENDER)
        ctx.skip_remaining()

        assert ctx.skip is True


# ============================================
# Plugin Loader Tests
# ============================================

class TestPluginLoader:
    """Test PluginLoader operations."""

    @pytest.fixture
    def loader(self):
        """Fresh loader with isolated registry."""
        registry = PluginRegistry()
        hook_manager = HookManager()
        return PluginLoader(registry=registry, hook_manager=hook_manager)

    def test_discover_plugins_empty(self, loader, tmp_path):
        """Test discovering plugins in empty directory."""
        plugins = loader.discover_plugins(str(tmp_path))
        assert plugins == []

    def test_discover_plugins_nonexistent(self, loader):
        """Test discovering plugins in non-existent directory."""
        plugins = loader.discover_plugins('/nonexistent/path')
        assert plugins == []

    def test_load_plugin_no_manifest(self, loader, tmp_path):
        """Test loading plugin without manifest fails."""
        with pytest.raises(PluginLoadError, match="Manifest not found"):
            loader.load_plugin(str(tmp_path))

    def test_load_plugin_invalid_manifest(self, loader, tmp_path):
        """Test loading plugin with invalid manifest."""
        manifest_file = tmp_path / 'quantum-plugin.yaml'
        manifest_file.write_text("invalid: [")

        with pytest.raises(PluginLoadError):
            loader.load_plugin(str(tmp_path))

    def test_get_loaded_plugins(self, loader):
        """Test getting list of loaded plugins."""
        plugins = loader.get_loaded_plugins()
        assert isinstance(plugins, list)


# ============================================
# Global Instance Tests
# ============================================

class TestGlobalInstances:
    """Test global instance getters/setters."""

    def test_get_registry_singleton(self):
        """Test get_registry returns singleton."""
        reg1 = get_registry()
        reg2 = get_registry()
        assert reg1 is reg2

    def test_set_registry(self):
        """Test setting custom registry."""
        original = get_registry()
        custom = PluginRegistry()
        set_registry(custom)

        assert get_registry() is custom

        # Restore original
        set_registry(original)

    def test_get_hook_manager_singleton(self):
        """Test get_hook_manager returns singleton."""
        hm1 = get_hook_manager()
        hm2 = get_hook_manager()
        assert hm1 is hm2

    def test_set_hook_manager(self):
        """Test setting custom hook manager."""
        original = get_hook_manager()
        custom = HookManager()
        set_hook_manager(custom)

        assert get_hook_manager() is custom

        # Restore original
        set_hook_manager(original)


# ============================================
# Tag Handler Tests
# ============================================

class TestTagHandler:
    """Test TagHandler base class."""

    def test_default_prefix(self):
        """Test default prefix is empty."""
        handler = TagHandler()
        assert handler.prefix == ""

    def test_parse_not_implemented(self):
        """Test parse raises NotImplementedError."""
        handler = TagHandler()
        with pytest.raises(NotImplementedError):
            handler.parse(None, None)

    def test_execute_returns_none(self):
        """Test execute returns None by default."""
        handler = TagHandler()
        result = handler.execute(None, None, None)
        assert result is None

    def test_render_returns_empty(self):
        """Test render returns empty string by default."""
        handler = TagHandler()
        result = handler.render(None, None)
        assert result == ""

    def test_get_supported_tags(self):
        """Test get_supported_tags returns empty list."""
        handler = TagHandler()
        tags = handler.get_supported_tags()
        assert tags == []


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
