"""
Unit Tests for Quantum Parser

Tests Phase 1 & Phase 2 parsing capabilities.
"""

import pytest
from core.parser import QuantumParser, QuantumParseError
from core.ast_nodes import (
    ComponentNode, SetNode, HTMLNode, TextNode,
    ImportNode, ComponentCallNode, SlotNode
)


class TestBasicParsing:
    """Test basic component parsing"""

    @pytest.mark.unit
    @pytest.mark.phase1
    def test_parse_simple_component(self, parser, tmp_path):
        """Test parsing a simple component"""
        comp_file = tmp_path / "simple.q"
        comp_file.write_text("""
<q:component name="Simple">
  <q:set name="message" value="Hello" />
  <h1>{message}</h1>
</q:component>
""")

        ast = parser.parse_file(str(comp_file))

        assert isinstance(ast, ComponentNode)
        assert ast.name == "Simple"
        assert len(ast.statements) >= 2  # set + html

    @pytest.mark.unit
    @pytest.mark.phase1
    def test_namespace_auto_injection(self, parser, tmp_path):
        """Test magic namespace injection"""
        comp_file = tmp_path / "no_namespace.q"
        comp_file.write_text("""
<q:component name="Test">
  <p>Hello</p>
</q:component>
""")

        # Should parse successfully without xmlns:q
        ast = parser.parse_file(str(comp_file))
        assert ast.name == "Test"

    @pytest.mark.unit
    @pytest.mark.phase1
    def test_databinding_detection(self, parser, tmp_path):
        """Test that databinding is detected in TextNodes"""
        comp_file = tmp_path / "binding.q"
        comp_file.write_text("""
<q:component name="Binding">
  <p>Hello {name}!</p>
</q:component>
""")

        ast = parser.parse_file(str(comp_file))
        # Should have HTMLNode with TextNode child
        html_node = ast.statements[0]
        assert isinstance(html_node, HTMLNode)
        assert len(html_node.children) > 0


class TestComponentComposition:
    """Test Phase 2 component composition parsing"""

    @pytest.mark.unit
    @pytest.mark.phase2
    def test_parse_import(self, parser, tmp_path):
        """Test parsing q:import"""
        comp_file = tmp_path / "with_import.q"
        comp_file.write_text("""
<q:component name="WithImport">
  <q:import component="Button" />
  <p>Test</p>
</q:component>
""")

        ast = parser.parse_file(str(comp_file))

        # Find ImportNode
        import_nodes = [s for s in ast.statements if isinstance(s, ImportNode)]
        assert len(import_nodes) == 1
        assert import_nodes[0].component == "Button"

    @pytest.mark.unit
    @pytest.mark.phase2
    def test_parse_component_call(self, parser, tmp_path):
        """Test parsing uppercase component calls"""
        comp_file = tmp_path / "with_call.q"
        comp_file.write_text("""
<q:component name="WithCall">
  <Button label="Click me" />
</q:component>
""")

        ast = parser.parse_file(str(comp_file))

        # Find ComponentCallNode
        calls = [s for s in ast.statements if isinstance(s, ComponentCallNode)]
        assert len(calls) == 1
        assert calls[0].component_name == "Button"
        assert calls[0].props.get('label') == "Click me"

    @pytest.mark.unit
    @pytest.mark.phase2
    def test_parse_slot(self, parser, tmp_path):
        """Test parsing q:slot"""
        comp_file = tmp_path / "with_slot.q"
        comp_file.write_text("""
<q:component name="WithSlot">
  <div>
    <q:slot />
  </div>
</q:component>
""")

        ast = parser.parse_file(str(comp_file))

        # Slot should be inside HTMLNode
        html_node = ast.statements[0]
        assert isinstance(html_node, HTMLNode)


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.unit
    def test_invalid_xml(self, parser, tmp_path):
        """Test that invalid XML raises error"""
        comp_file = tmp_path / "invalid.q"
        comp_file.write_text("<q:component>Not closed")

        with pytest.raises(QuantumParseError):
            parser.parse_file(str(comp_file))

    @pytest.mark.unit
    def test_file_not_found(self, parser):
        """Test file not found error"""
        with pytest.raises(QuantumParseError, match="File not found"):
            parser.parse_file("nonexistent.q")
