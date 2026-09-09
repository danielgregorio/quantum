"""
The production entry point had 0% coverage.

DEPLOYMENT.md tells people to serve Quantum through a WSGI server, and
quantum/runtime/wsgi.py is the module that exists for exactly that. Nothing
imported it. Its own usage comment said `gunicorn "src.runtime.wsgi:app"` —
the layout that stopped existing when src/ became the quantum/ package — so
the documented command in the file whose only purpose is being that command
did not import.

A deployment path nobody executes is a deployment path nobody knows is
broken.
"""

import subprocess
import sys

import pytest

pytest.importorskip("flask")


@pytest.fixture(scope="module")
def wsgi():
    from quantum.runtime import wsgi as module
    return module


class TestTheFactory:
    def test_create_app_returns_a_wsgi_application(self, wsgi):
        app = wsgi.create_app()
        assert callable(app), "gunicorn calls this; it has to be callable"
        assert hasattr(app, "wsgi_app")

    def test_the_module_level_app_exists(self, wsgi):
        # `gunicorn quantum.runtime.wsgi:app` needs this name to be bound.
        assert wsgi.app is not None

    def test_the_alternative_factory_works(self, wsgi):
        # `gunicorn "quantum.runtime.wsgi:get_app()"`
        assert wsgi.get_app() is not None

    def test_it_serves_the_health_check(self, wsgi):
        # DEPLOYMENT.md wires /health to the container readiness probe.
        response = wsgi.create_app().test_client().get("/health")
        assert response.status_code == 200
        assert b"healthy" in response.data

    def test_a_missing_config_path_falls_back_instead_of_crashing(self, wsgi):
        app = wsgi.create_app(config_path="/nao/existe/quantum.config.yaml")
        assert app is not None


class TestTheDocumentedCommandImports:
    """The failure mode here is a deploy that dies at startup."""

    @pytest.mark.parametrize("target", [
        "quantum.runtime.wsgi:app",
        "quantum.runtime.wsgi:create_app",
        "quantum.runtime.web_server:create_app",
    ])
    def test_the_target_resolves(self, target):
        module_name, attribute = target.split(":")
        result = subprocess.run(
            [sys.executable, "-c",
             f"import importlib;m=importlib.import_module('{module_name}');"
             f"assert getattr(m,'{attribute}') is not None;print('ok')"],
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, result.stderr[-800:]

    def test_no_runnable_command_still_names_the_dead_src_path(self):
        # The failure mode is a COMMAND that does not import, not a comment
        # explaining that it used to. So the check is for a line that both
        # invokes a server and names the old path — matching the bare string
        # flags the very comments that document this fix.
        import pathlib
        import re

        repo = pathlib.Path(__file__).resolve().parents[2]
        offenders = []

        for path in list((repo / "quantum").rglob("*.py")) + [
                repo / "DEPLOYMENT.md", repo / "README.md"]:
            if not path.is_file():
                continue
            in_code_block = False
            for number, line in enumerate(
                    path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if path.suffix == ".md":
                    if line.lstrip().startswith("```"):
                        in_code_block = not in_code_block
                        continue
                    # Only a fenced block is a command to run; a blockquote
                    # is commentary, and this repository's docs explain the
                    # old path in prose on purpose.
                    if not in_code_block:
                        continue
                if not re.search(r"gunicorn|waitress-serve", line):
                    continue
                if re.search(r"\bsrc\.runtime\.", line):
                    offenders.append(f"{path.name}:{number} {line.strip()[:70]}")

        assert offenders == [], offenders
