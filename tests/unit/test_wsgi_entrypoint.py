"""
The one documented production entry point did not import.

create_app's docstring said `gunicorn 'src.runtime.web_server:create_app()'` —
the layout that stopped existing when src/ became the quantum/ package. Anyone
following DEPLOYMENT instructions hit ModuleNotFoundError on the first command.

The secret-key warning matters just as much: without QUANTUM_SECRET_KEY each
gunicorn worker generates its OWN random session key at import, so a cookie
signed by one worker is rejected by the next and users are logged out at
random — a bug that takes days to chase because it looks intermittent.
"""

import logging
import pathlib

import pytest

from quantum.runtime.web_server import create_app


class TestTheFactoryWorks:
    def test_it_returns_a_flask_app(self):
        from flask import Flask
        assert isinstance(create_app(), Flask)

    def test_the_app_serves_health(self):
        assert create_app().test_client().get("/health").status_code == 200

    def test_the_app_serves_a_component(self, tmp_path):
        # A project of its own. This used to serve the repo's /admin/projects,
        # which reads the admin database — it passed only because the admin
        # tests, run earlier, created quantum_admin/quantum_admin.db in the
        # checkout. Once those tests stopped writing to the real database, a
        # clean CI clone had no tables and this answered 500.
        components = tmp_path / "components"
        components.mkdir()
        (components / "ola.q").write_text(
            '<q:component name="ola" xmlns:q="https://quantum.lang/ns">'
            '<q:set name="n" value="41" type="number" />'
            '<html><body><p>resposta {n + 1}</p></body></html></q:component>',
            encoding="utf-8")
        config = tmp_path / "quantum.config.yaml"
        config.write_text(
            f"paths:\n  components: {components.as_posix()}\n"
            "logging:\n  console: false\n  file: false\n", encoding="utf-8")
        resp = create_app(str(config)).test_client().get("/ola")
        assert resp.status_code == 200
        assert "resposta 42" in resp.get_data(as_text=True)


class TestTheDocumentedPathIsReal:
    def test_the_docstring_gives_the_working_command(self):
        src = create_app.__doc__ or ""
        assert "quantum.runtime.web_server:create_app" in src
        # `src.runtime` may still appear in prose explaining the old bug; what
        # must not exist is a gunicorn COMMAND naming it.
        assert "gunicorn 'src.runtime" not in src

    def test_the_module_path_actually_imports(self):
        """The real check: the string in the docs resolves."""
        import importlib
        mod = importlib.import_module("quantum.runtime.web_server")
        assert callable(getattr(mod, "create_app"))

    def test_the_deployment_doc_uses_the_same_path(self):
        doc = pathlib.Path(__file__).resolve().parents[2] / "DEPLOYMENT.md"
        text = doc.read_text(encoding="utf-8")
        assert "quantum.runtime.web_server:create_app" in text


class TestTheSecretKeyWarning:
    def test_it_warns_when_unset(self, monkeypatch, caplog):
        monkeypatch.delenv("QUANTUM_SECRET_KEY", raising=False)
        with caplog.at_level(logging.WARNING, logger="quantum"):
            create_app()
        assert "SECRET_KEY" in caplog.text
        assert "logged out" in caplog.text

    def test_it_is_silent_when_set(self, monkeypatch, caplog):
        monkeypatch.setenv("QUANTUM_SECRET_KEY", "x" * 32)
        with caplog.at_level(logging.WARNING, logger="quantum"):
            create_app()
        assert "SECRET_KEY" not in caplog.text
