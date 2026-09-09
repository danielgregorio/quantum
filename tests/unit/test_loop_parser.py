"""
Regression tests for LoopParser type inference.

Found in the 2026-09 audit: <q:loop items="..." var="..."> with no explicit
type= was always classified as a range loop (get_attr default was 'range'),
so it failed validation with "Range loop requires 'from' attribute" even
though items= was present. Confirmed breaking examples across unrelated
features (agents, data_import, scripting) — see FULL_AUDIT_2026-09.md.
"""

from unittest.mock import MagicMock
from xml.etree import ElementTree as ET
from quantum.core.parsers.control_flow.loop_parser import LoopParser


def _parse(xml: str):
    element = ET.fromstring(xml)
    return LoopParser(MagicMock()).parse(element)


class TestLoopTypeInference:
    def test_items_without_type_infers_array(self):
        node = _parse('<loop items="{users}" var="user">text</loop>')
        assert node.loop_type == 'array'
        assert node.items == '{users}'
        assert not node.validate()

    def test_no_items_and_no_type_defaults_to_range(self):
        node = _parse('<loop var="i" from="1" to="10">text</loop>')
        assert node.loop_type == 'range'
        assert not node.validate()

    def test_explicit_type_wins_over_items_presence(self):
        node = _parse('<loop items="1,2,3" type="list" var="n">text</loop>')
        assert node.loop_type == 'list'

    def test_items_without_type_and_without_var_still_reports_missing_var(self):
        try:
            _parse('<loop items="{users}">text</loop>')
            assert False, "expected ParserError"
        except Exception as e:
            assert "var" in str(e).lower()
