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

    def test_the_app_serves_a_component(self):
        resp = create_app().test_client().get("/admin/projects")
        assert resp.status_code == 200


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
