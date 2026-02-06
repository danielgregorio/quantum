"""
Tests for Quantum LSP server functionality.
"""

import pytest
from lsprotocol import types

from quantum_lsp.server import QuantumLanguageServer, create_server
from quantum_lsp.analysis.document import QuantumDocument
from quantum_lsp.analysis.symbols import SymbolTable, Symbol, SymbolKind
from quantum_lsp.schema import get_tag_info, get_all_tags, QUANTUM_TAGS
from quantum_lsp.schema.attributes import get_attributes_for_tag, get_required_attributes
from quantum_lsp.utils.position import offset_to_position, position_to_offset


class TestPositionUtils:
    """Test position utility functions."""

    def test_offset_to_position_simple(self):
        text = "hello\nworld"
        assert offset_to_position(text, 0) == (0, 0)
        assert offset_to_position(text, 5) == (0, 5)
        assert offset_to_position(text, 6) == (1, 0)
        assert offset_to_position(text, 7) == (1, 1)

    def test_position_to_offset_simple(self):
        text = "hello\nworld"
        assert position_to_offset(text, 0, 0) == 0
        assert position_to_offset(text, 0, 5) == 5
        assert position_to_offset(text, 1, 0) == 6
        assert position_to_offset(text, 1, 2) == 8


class TestSchema:
    """Test schema definitions."""

    def test_get_tag_info(self):
        info = get_tag_info("q:set")
        assert info is not None
        assert info.name == "set"
        assert info.namespace == "q"
        assert "name" in info.attributes

    def test_get_unknown_tag(self):
        info = get_tag_info("q:nonexistent")
        assert info is None

    def test_all_tags_have_description(self):
        for tag_name, tag_info in QUANTUM_TAGS.items():
            assert tag_info.description, f"Tag {tag_name} missing description"

    def test_required_attributes(self):
        # q:set requires 'name'
        required = get_required_attributes("q:set")
        assert "name" in required

        # q:component requires 'name'
        required = get_required_attributes("q:component")
        assert "name" in required

        # q:query requires 'name'
        required = get_required_attributes("q:query")
        assert "name" in required


class TestDocument:
    """Test document parsing and analysis."""

    def test_parse_simple_component(self):
        text = '''<q:component name="Test">
  <q:set name="counter" type="integer" value="0" />
</q:component>'''

        doc = QuantumDocument("file:///test.q", text)
        assert doc.get_parse_error() is None

        # Should find component symbol
        components = doc.symbols.get_components()
        assert len(components) == 1
        assert components[0].name == "Test"

        # Should find variable symbol
        variables = doc.symbols.get_variables()
        assert len(variables) == 1
        assert variables[0].name == "counter"

    def test_parse_function(self):
        text = '''<q:component name="Test">
  <q:function name="greet" returnType="string">
    <q:param name="name" type="string" />
    <q:return value="Hello, {name}!" />
  </q:function>
</q:component>'''

        doc = QuantumDocument("file:///test.q", text)
        assert doc.get_parse_error() is None

        functions = doc.symbols.get_functions()
        assert len(functions) == 1
        assert functions[0].name == "greet"
        assert functions[0].type_hint == "string"

    def test_parse_query(self):
        text = '''<q:component name="Test">
  <q:query name="users" datasource="db">
    SELECT * FROM users
  </q:query>
</q:component>'''

        doc = QuantumDocument("file:///test.q", text)

        queries = doc.symbols.get_queries()
        assert len(queries) == 1
        assert queries[0].name == "users"

    def test_context_detection_tag_name(self):
        text = '<q:se'
        doc = QuantumDocument("file:///test.q", text)

        context = doc.get_context_at_position(0, 5)
        assert context["context"] == "tag_name"
        assert context["prefix"] == "q:se"

    def test_context_detection_attribute_name(self):
        text = '<q:set na'
        doc = QuantumDocument("file:///test.q", text)

        context = doc.get_context_at_position(0, 9)
        assert context["context"] == "attribute_name"
        assert context["tag"] == "q:set"

    def test_context_detection_attribute_value(self):
        text = '<q:set name="cou'
        doc = QuantumDocument("file:///test.q", text)

        context = doc.get_context_at_position(0, 16)
        assert context["context"] == "attribute_value"
        assert context["attribute"] == "name"

    def test_context_detection_databinding(self):
        text = '<p>{use'
        doc = QuantumDocument("file:///test.q", text)

        context = doc.get_context_at_position(0, 7)
        assert context["context"] == "databinding"
        assert context["inside_databinding"] == True

    def test_diagnostics_missing_required(self):
        # q:set without name attribute
        text = '<q:set type="string" />'
        doc = QuantumDocument("file:///test.q", text)

        diagnostics = doc.get_diagnostics()
        assert len(diagnostics) > 0
        assert any("name" in d.message.lower() for d in diagnostics)


class TestSymbolTable:
    """Test symbol table functionality."""

    def test_add_and_get_symbol(self):
        table = SymbolTable("file:///test.q")

        symbol = Symbol(
            name="counter",
            kind=SymbolKind.VARIABLE,
            line=1,
            column=0,
            end_line=1,
            end_column=10,
            uri="file:///test.q",
            type_hint="integer"
        )

        table.add_symbol(symbol)

        result = table.get_symbol("counter", SymbolKind.VARIABLE)
        assert result is not None
        assert result.name == "counter"

    def test_find_definition(self):
        table = SymbolTable("file:///test.q")

        table.add_symbol(Symbol(
            name="myVar",
            kind=SymbolKind.VARIABLE,
            line=1, column=0, end_line=1, end_column=10,
            uri="file:///test.q"
        ))

        table.add_symbol(Symbol(
            name="myFunc",
            kind=SymbolKind.FUNCTION,
            line=5, column=0, end_line=10, end_column=10,
            uri="file:///test.q"
        ))

        var = table.find_definition("myVar")
        assert var is not None
        assert var.kind == SymbolKind.VARIABLE

        func = table.find_definition("myFunc")
        assert func is not None
        assert func.kind == SymbolKind.FUNCTION


class TestServer:
    """Test server creation."""

    def test_create_server(self):
        server = create_server()
        assert server is not None
        assert isinstance(server, QuantumLanguageServer)


# Integration tests would require more setup with actual LSP communication
# These are typically done with end-to-end testing frameworks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
