"""
Tests for State Persistence feature.

This module tests:
- SetNode persist attribute parsing
- PersistNode parsing
- HTML persistence JS generation
- Desktop persistence code generation
"""

import pytest
import sys
import os
from pathlib import Path

# Add src to path for imports
_src_path = str(Path(__file__).parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Change to src directory for relative imports to work
os.chdir(_src_path)

from core.parser import QuantumParser, QuantumParseError
from core.ast_nodes import SetNode, PersistNode
from runtime.ui_html_templates import (
    PERSISTENCE_JS,
    generate_persistence_registration,
)


class TestSetNodePersist:
    """Tests for SetNode persist attribute."""

    def test_set_node_has_persist_attribute(self):
        """SetNode should have persist attribute."""
        node = SetNode("theme")
        assert hasattr(node, "persist")
        assert node.persist is None

    def test_set_node_persist_scopes(self):
        """SetNode should accept valid persist scopes."""
        for scope in ["local", "session", "sync"]:
            node = SetNode("theme")
            node.persist = scope
            errors = node.validate()
            assert not errors, f"Scope '{scope}' should be valid"

    def test_set_node_invalid_persist_scope(self):
        """SetNode should reject invalid persist scopes."""
        node = SetNode("theme")
        node.persist = "invalid"
        errors = node.validate()
        assert len(errors) == 1
        assert "Invalid persist scope" in errors[0]

    def test_set_node_persist_to_dict(self):
        """SetNode to_dict should include persistence info."""
        node = SetNode("theme")
        node.persist = "local"
        node.persist_key = "app_theme"
        node.persist_ttl = 3600
        node.persist_encrypt = True

        result = node.to_dict()
        assert "persistence" in result
        assert result["persistence"]["scope"] == "local"
        assert result["persistence"]["key"] == "app_theme"
        assert result["persistence"]["ttl"] == 3600
        assert result["persistence"]["encrypt"] is True

    def test_set_node_no_persistence_in_dict(self):
        """SetNode to_dict should not include persistence if not set."""
        node = SetNode("counter")
        node.value = "0"

        result = node.to_dict()
        assert "persistence" not in result


class TestPersistNode:
    """Tests for PersistNode."""

    def test_persist_node_creation(self):
        """PersistNode should be created with defaults."""
        node = PersistNode()
        assert node.scope == "local"
        assert node.prefix is None
        assert node.key is None
        assert node.encrypt is False
        assert node.ttl is None
        assert node.storage is None
        assert node.variables == []

    def test_persist_node_add_variable(self):
        """PersistNode should allow adding variables."""
        node = PersistNode()
        node.add_variable("theme")
        node.add_variable("locale")

        assert "theme" in node.variables
        assert "locale" in node.variables
        assert len(node.variables) == 2

    def test_persist_node_validation_no_vars(self):
        """PersistNode should require at least one variable."""
        node = PersistNode()
        errors = node.validate()
        assert len(errors) == 1
        assert "at least one q:var" in errors[0]

    def test_persist_node_validation_invalid_scope(self):
        """PersistNode should reject invalid scope."""
        node = PersistNode(scope="invalid")
        node.add_variable("test")
        errors = node.validate()
        assert any("Invalid persist scope" in e for e in errors)

    def test_persist_node_validation_invalid_storage(self):
        """PersistNode should reject invalid storage backend."""
        node = PersistNode(storage="invalidBackend")
        node.add_variable("test")
        errors = node.validate()
        assert any("Invalid storage backend" in e for e in errors)

    def test_persist_node_to_dict(self):
        """PersistNode to_dict should return correct structure."""
        node = PersistNode(
            scope="sync",
            prefix="myapp_",
            key="user_prefs",
            encrypt=True,
            ttl=7200
        )
        node.add_variable("theme")
        node.add_variable("fontSize")

        result = node.to_dict()
        assert result["type"] == "persist"
        assert result["scope"] == "sync"
        assert result["prefix"] == "myapp_"
        assert result["key"] == "user_prefs"
        assert result["encrypt"] is True
        assert result["ttl"] == 7200
        assert "theme" in result["variables"]
        assert "fontSize" in result["variables"]


class TestParserPersistAttribute:
    """Tests for parsing persist attribute on q:set."""

    def setup_method(self):
        self.parser = QuantumParser()

    def test_parse_set_with_persist_local(self):
        """Parser should parse persist='local' on q:set."""
        source = '''
        <q:component name="TestPersist">
            <q:set name="theme" value="dark" persist="local" />
        </q:component>
        '''
        ast = self.parser.parse(source)
        set_node = ast.statements[0]

        assert isinstance(set_node, SetNode)
        assert set_node.name == "theme"
        assert set_node.persist == "local"

    def test_parse_set_with_persist_session(self):
        """Parser should parse persist='session' on q:set."""
        source = '''
        <q:component name="TestPersist">
            <q:set name="cartItems" value="[]" persist="session" />
        </q:component>
        '''
        ast = self.parser.parse(source)
        set_node = ast.statements[0]

        assert set_node.persist == "session"

    def test_parse_set_with_persist_sync(self):
        """Parser should parse persist='sync' on q:set."""
        source = '''
        <q:component name="TestPersist">
            <q:set name="settings" value="{}" persist="sync" />
        </q:component>
        '''
        ast = self.parser.parse(source)
        set_node = ast.statements[0]

        assert set_node.persist == "sync"

    def test_parse_set_with_persist_key(self):
        """Parser should parse persistKey on q:set."""
        source = '''
        <q:component name="TestPersist">
            <q:set name="theme" value="dark" persist="local" persistKey="app_theme_v2" />
        </q:component>
        '''
        ast = self.parser.parse(source)
        set_node = ast.statements[0]

        assert set_node.persist_key == "app_theme_v2"

    def test_parse_set_with_persist_ttl(self):
        """Parser should parse persistTtl on q:set."""
        source = '''
        <q:component name="TestPersist">
            <q:set name="cache" value="{}" persist="local" persistTtl="3600" />
        </q:component>
        '''
        ast = self.parser.parse(source)
        set_node = ast.statements[0]

        assert set_node.persist_ttl == 3600

    def test_parse_set_with_persist_encrypt(self):
        """Parser should parse persistEncrypt on q:set."""
        source = '''
        <q:component name="TestPersist">
            <q:set name="token" value="" persist="local" persistEncrypt="true" />
        </q:component>
        '''
        ast = self.parser.parse(source)
        set_node = ast.statements[0]

        assert set_node.persist_encrypt is True


class TestParserPersistTag:
    """Tests for parsing q:persist tag."""

    def setup_method(self):
        self.parser = QuantumParser()

    def test_parse_persist_tag_basic(self):
        """Parser should parse basic q:persist tag."""
        source = '''
        <q:component name="TestPersist">
            <q:persist scope="local">
                <q:var name="theme" />
                <q:var name="locale" />
            </q:persist>
        </q:component>
        '''
        ast = self.parser.parse(source)
        persist_node = ast.statements[0]

        assert isinstance(persist_node, PersistNode)
        assert persist_node.scope == "local"
        assert "theme" in persist_node.variables
        assert "locale" in persist_node.variables

    def test_parse_persist_tag_with_prefix(self):
        """Parser should parse q:persist with prefix."""
        source = '''
        <q:component name="TestPersist">
            <q:persist scope="local" prefix="myapp_">
                <q:var name="setting1" />
            </q:persist>
        </q:component>
        '''
        ast = self.parser.parse(source)
        persist_node = ast.statements[0]

        assert persist_node.prefix == "myapp_"

    def test_parse_persist_tag_with_key(self):
        """Parser should parse q:persist with unified key."""
        source = '''
        <q:component name="TestPersist">
            <q:persist scope="sync" key="user_preferences">
                <q:var name="theme" />
                <q:var name="fontSize" />
            </q:persist>
        </q:component>
        '''
        ast = self.parser.parse(source)
        persist_node = ast.statements[0]

        assert persist_node.key == "user_preferences"

    def test_parse_persist_tag_with_encrypt(self):
        """Parser should parse q:persist with encrypt."""
        source = '''
        <q:component name="TestPersist">
            <q:persist scope="local" encrypt="true">
                <q:var name="apiKey" />
            </q:persist>
        </q:component>
        '''
        ast = self.parser.parse(source)
        persist_node = ast.statements[0]

        assert persist_node.encrypt is True

    def test_parse_persist_tag_with_ttl(self):
        """Parser should parse q:persist with ttl."""
        source = '''
        <q:component name="TestPersist">
            <q:persist scope="local" ttl="7200">
                <q:var name="cache" />
            </q:persist>
        </q:component>
        '''
        ast = self.parser.parse(source)
        persist_node = ast.statements[0]

        assert persist_node.ttl == 7200


class TestHtmlPersistenceJS:
    """Tests for HTML persistence JavaScript generation."""

    def test_persistence_js_contains_backends(self):
        """PERSISTENCE_JS should contain storage backends."""
        assert "local:" in PERSISTENCE_JS
        assert "session:" in PERSISTENCE_JS
        assert "sync:" in PERSISTENCE_JS

    def test_persistence_js_contains_register(self):
        """PERSISTENCE_JS should contain register function."""
        assert "register:" in PERSISTENCE_JS
        assert "__quantumPersist" in PERSISTENCE_JS

    def test_persistence_js_contains_save_load(self):
        """PERSISTENCE_JS should contain save and load functions."""
        assert "save:" in PERSISTENCE_JS
        assert "load:" in PERSISTENCE_JS

    def test_persistence_js_contains_ttl_check(self):
        """PERSISTENCE_JS should handle TTL expiration."""
        assert "_ttl" in PERSISTENCE_JS
        assert "Date.now()" in PERSISTENCE_JS

    def test_generate_persistence_registration_empty(self):
        """generate_persistence_registration should return empty for no vars."""
        result = generate_persistence_registration([])
        assert result == ''

    def test_generate_persistence_registration_basic(self):
        """generate_persistence_registration should generate registration code."""
        vars = [
            {'name': 'theme', 'scope': 'local', 'key': 'theme'}
        ]
        result = generate_persistence_registration(vars)

        assert '<script>' in result
        assert 'DOMContentLoaded' in result
        assert "__quantumPersist.register('theme', 'local'" in result
        assert "__quantumPersist.load('theme')" in result

    def test_generate_persistence_registration_with_ttl(self):
        """generate_persistence_registration should include TTL."""
        vars = [
            {'name': 'cache', 'scope': 'local', 'key': 'cache', 'ttl': 3600}
        ]
        result = generate_persistence_registration(vars)

        assert "ttl: 3600" in result

    def test_generate_persistence_registration_with_encrypt(self):
        """generate_persistence_registration should include encrypt flag."""
        vars = [
            {'name': 'token', 'scope': 'local', 'key': 'token', 'encrypt': True}
        ]
        result = generate_persistence_registration(vars)

        assert "encrypt: true" in result


class TestDesktopPersistence:
    """Tests for desktop persistence code generation."""

    def test_quantum_state_has_persistence_methods(self):
        """QuantumState template should have persistence methods."""
        from runtime.ui_desktop_templates import QUANTUM_STATE_CLASS

        assert "_persist_config" in QUANTUM_STATE_CLASS
        assert "_persist_value" in QUANTUM_STATE_CLASS
        assert "_restore_persisted" in QUANTUM_STATE_CLASS
        assert "restore_all_persisted" in QUANTUM_STATE_CLASS
        assert "remove_persisted" in QUANTUM_STATE_CLASS

    def test_quantum_state_uses_file_storage(self):
        """QuantumState template should use file storage for desktop."""
        from runtime.ui_desktop_templates import QUANTUM_STATE_CLASS

        assert "_get_storage_path" in QUANTUM_STATE_CLASS
        assert "os.path.join" in QUANTUM_STATE_CLASS
        assert ".json" in QUANTUM_STATE_CLASS

    def test_quantum_api_accepts_persist_config(self):
        """QuantumAPI template should accept persist_config."""
        from runtime.ui_desktop_templates import QUANTUM_API_CLASS

        assert "persist_config" in QUANTUM_API_CLASS
        assert "QuantumState(window, self._persist_config)" in QUANTUM_API_CLASS

    def test_quantum_api_restores_on_init(self):
        """QuantumAPI template should restore persisted values on init."""
        from runtime.ui_desktop_templates import QUANTUM_API_CLASS

        assert "restore_all_persisted" in QUANTUM_API_CLASS

    def test_desktop_adapter_generates_persist_config(self):
        """UIDesktopAdapter should generate persist config."""
        try:
            from runtime.ui_desktop_adapter import UIDesktopAdapter
        except ImportError as e:
            pytest.skip(f"UIDesktopAdapter import failed (theming dependency): {e}")

        adapter = UIDesktopAdapter()
        adapter._persist_config = {
            'theme': {'scope': 'local', 'key': 'theme', 'encrypt': False}
        }

        config_str = adapter._generate_persist_config()

        assert "'theme'" in config_str
        assert "'scope': 'local'" in config_str


class TestIntegrationPersistence:
    """Integration tests for state persistence."""

    def setup_method(self):
        self.parser = QuantumParser()

    def test_full_persist_flow_parsing(self):
        """Test complete persistence flow from parsing to AST."""
        source = '''
        <q:component name="SettingsApp">
            <q:set name="theme" value="dark" persist="local" persistKey="user_theme" />
            <q:set name="fontSize" value="16" persist="local" />
            <q:set name="tempData" value="" />

            <q:persist scope="sync" prefix="prefs_">
                <q:var name="notifications" />
                <q:var name="language" />
            </q:persist>
        </q:component>
        '''
        ast = self.parser.parse(source)

        # Check q:set with persist
        theme_node = ast.statements[0]
        assert theme_node.persist == "local"
        assert theme_node.persist_key == "user_theme"

        font_node = ast.statements[1]
        assert font_node.persist == "local"
        assert font_node.persist_key is None

        temp_node = ast.statements[2]
        assert temp_node.persist is None

        # Check q:persist
        persist_node = ast.statements[3]
        assert isinstance(persist_node, PersistNode)
        assert persist_node.scope == "sync"
        assert persist_node.prefix == "prefs_"
        assert len(persist_node.variables) == 2
