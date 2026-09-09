"""
The support surface is enforced in code (PRODUCTION_READINESS.md Fase 0).

An experimental tag still runs, but the operator is told once that they are
leaning on something the project does not promise to keep working — the audit
found apps built entirely on tags that parse and then explode, with nothing
warning anyone.
"""

import logging

import pytest

from quantum.core import tiers


@pytest.fixture(autouse=True)
def fresh():
    tiers.reset_warnings()
    yield
    tiers.reset_warnings()


class TestClassification:
    def test_core(self):
        assert tiers.tier_of("query") == "core"
        assert tiers.tier_of("if") == "core"

    def test_diferencial(self):
        assert tiers.tier_of("agent") == "diferencial"

    def test_experimental(self):
        assert tiers.tier_of("job") == "experimental"
        assert tiers.tier_of("websocket") == "experimental"

    def test_unknown(self):
        assert tiers.tier_of("onEvent") == "unknown"

    def test_core_and_diferencial_do_not_overlap_experimental(self):
        assert not (tiers.SUPPORTED & tiers.EXPERIMENTAL)


class TestWarning:
    def test_core_tag_is_silent(self, caplog):
        with caplog.at_level(logging.WARNING, logger="quantum.tiers"):
            tiers.warn_if_unsupported("query")
        assert not caplog.records

    def test_experimental_tag_warns(self, caplog):
        with caplog.at_level(logging.WARNING, logger="quantum.tiers"):
            tiers.warn_if_unsupported("job")
        assert len(caplog.records) == 1
        assert "EXPERIMENTAL" in caplog.text

    def test_warns_once_per_tag(self, caplog):
        with caplog.at_level(logging.WARNING, logger="quantum.tiers"):
            for _ in range(1000):
                tiers.warn_if_unsupported("mail")
        assert len(caplog.records) == 1

    def test_unknown_tag_is_left_to_the_parser(self, caplog):
        # Unknown tags are an error the parser reports; tiers stays quiet.
        with caplog.at_level(logging.WARNING, logger="quantum.tiers"):
            tiers.warn_if_unsupported("nosuchtag")
        assert not caplog.records


class TestFiresDuringParsing:
    def test_an_experimental_tag_in_a_document_warns_once(self, caplog):
        from quantum.core.parser import QuantumParser
        src = (
            '<q:component name="T">'
            '<q:log message="a" /><q:log message="b" />'
            '</q:component>'
        )
        with caplog.at_level(logging.WARNING, logger="quantum.tiers"):
            QuantumParser().parse(src)
        tier_lines = [r for r in caplog.records if "EXPERIMENTAL" in r.message]
        assert len(tier_lines) == 1
