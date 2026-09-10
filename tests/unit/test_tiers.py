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


class TestApplicationTypes:
    """D1/D2: the game engine stays in the repo as LABORATÓRIO, not parked."""

    def test_game_is_laboratorio(self):
        assert tiers.app_tier_of("game") == "laboratorio"

    def test_alternative_targets_are_experimental(self):
        for app_type in ("terminal", "ui", "microservices"):
            assert tiers.app_tier_of(app_type) == "experimental"

    def test_declared_web_applications_are_experimental(self):
        # G17/G18: q:application type html does not start, and type api does
        # not execute route bodies. Web apps are pages in components/.
        assert tiers.app_tier_of("html") == "experimental"
        assert tiers.app_tier_of("api") == "experimental"

    def test_an_unknown_type_is_not_flagged_here(self):
        assert tiers.app_tier_of("job") == "supported"

    def test_auth_attributes_are_core(self):
        # D4: authentication is Core, expressed as component attributes.
        assert {"require_auth", "require_role"} <= tiers.CORE_ATTRIBUTES

    def test_lab_warning_says_laboratorio_once(self, caplog):
        with caplog.at_level(logging.WARNING, logger="quantum.tiers"):
            for _ in range(5):
                tiers.warn_app_type("game")
        assert len(caplog.records) == 1
        assert "LABORATÓRIO" in caplog.text

    def test_supported_type_is_silent(self, caplog):
        with caplog.at_level(logging.WARNING, logger="quantum.tiers"):
            tiers.warn_app_type("job")
        assert not caplog.records

    def test_running_a_game_warns(self, tmp_path):
        import os
        import subprocess
        import sys
        from pathlib import Path
        game = tmp_path / "g.q"
        game.write_text(
            '<q:application id="g" type="game" xmlns:q="https://quantum.lang/ns" '
            'xmlns:qg="https://quantum.lang/game">'
            '<qg:scene name="main" width="100" height="100"></qg:scene>'
            '</q:application>', encoding="utf-8")
        repo = Path(__file__).resolve().parents[2]
        out = subprocess.run([sys.executable, "-m", "quantum.cli.runner", "run", str(game)],
                             capture_output=True, text=True, cwd=tmp_path, timeout=120,
                             env=dict(os.environ, PYTHONPATH=str(repo), PYTHONIOENCODING="utf-8"),
                             encoding="utf-8", errors="replace")
        assert "LABORATÓRIO" in out.stdout + out.stderr


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
