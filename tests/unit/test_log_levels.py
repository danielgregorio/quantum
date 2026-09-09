"""
`level="warn"` was a parse error, and it is what everyone writes.

Python's logging, JavaScript's console and most log libraries call it warn.
Two examples in this repository used it — one of them the only q:websocket
example there is, so the tag's only example did not parse, which is how it
appeared in FEATURE_STATUS.md as an unparseable feature.
"""

import pytest

from quantum.core.features.logging.src.ast_node import LogNode


class TestTheSpellingsPeopleUse:
    @pytest.mark.parametrize("written,meant", [
        ("warn", "warning"),
        ("fatal", "critical"),
        ("err", "error"),
        ("verbose", "trace"),
        ("WARN", "warning"),
        (" warn ", "warning"),
    ])
    def test_an_alias_becomes_the_real_level(self, written, meant):
        assert LogNode(level=written, message="oi").level == meant

    @pytest.mark.parametrize("level", [
        "trace", "debug", "info", "warning", "error", "critical",
    ])
    def test_the_real_levels_are_unchanged(self, level):
        assert LogNode(level=level, message="oi").level == level

    def test_something_that_is_not_a_level_is_still_refused(self):
        with pytest.raises(ValueError, match="Invalid log level"):
            LogNode(level="gritar", message="oi")

    def test_a_missing_level_is_still_refused(self):
        with pytest.raises(ValueError, match="requires"):
            LogNode(level="", message="oi")

    def test_validate_agrees_with_the_constructor(self):
        # validate() checks self.level, which __init__ has normalised — if
        # those two ever disagree, a node builds and then reports itself
        # invalid.
        assert LogNode(level="warn", message="oi").validate() == []


class TestTheExamplesParse:
    @pytest.mark.parametrize("path", [
        "examples/websocket-chat.q",
        "examples/message_queue_demo.q",
    ])
    def test_the_files_that_used_warn(self, path):
        import pathlib
        from quantum.core.parser import QuantumParser

        repo = pathlib.Path(__file__).resolve().parents[2]
        QuantumParser().parse_file(str(repo / path))
