"""Isolamento dos testes dos serviços do admin (quantum_admin/services).

Os serviços usam a biblioteca do backend, que tem caminhos e singletons de
módulo: o banco (database.engine), settings/connectors.yaml
(connector_service), settings/global.yaml (settings_service). Sem redirecionar
todos, um teste de connector gravaria no connectors.yaml real do dono.
"""

import hashlib
import pathlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SETTINGS_REAIS = pathlib.Path(__file__).resolve().parents[2] / "quantum_admin" / "settings"


def _impressao_digital():
    if not SETTINGS_REAIS.is_dir():
        return {}
    return {str(p.relative_to(SETTINGS_REAIS)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(SETTINGS_REAIS.rglob("*")) if p.is_file() and p.suffix in (".yaml", ".yml", ".json")}


@pytest.fixture(scope="session", autouse=True)
def settings_reais_intocados():
    """Os dados do dono em quantum_admin/settings não podem mudar por causa da suíte."""
    antes = _impressao_digital()
    yield
    depois = _impressao_digital()
    mudou = sorted(k for k in set(antes) | set(depois) if antes.get(k) != depois.get(k))
    assert not mudou, f"a suíte do admin alterou dados reais em quantum_admin/settings: {mudou}"


@pytest.fixture
def admin_isolado(tmp_path, monkeypatch):
    from quantum_admin.backend import connector_service, database, settings_service
    from quantum_admin.services import _base

    engine = create_engine(f"sqlite:///{(tmp_path / 'admin.db').as_posix()}",
                           connect_args={"check_same_thread": False})
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    monkeypatch.setattr(_base, "_iniciado", False)

    settings = tmp_path / "quantum_admin" / "settings"
    settings.mkdir(parents=True)
    monkeypatch.setenv("QUANTUM_ADMIN_ROOT", str(tmp_path))
    monkeypatch.setenv("QUANTUM_ADMIN_SETTINGS_DIR", str(settings))

    monkeypatch.setattr(connector_service, "SETTINGS_DIR", settings)
    monkeypatch.setattr(connector_service, "CONNECTORS_FILE", settings / "connectors.yaml")
    monkeypatch.setattr(connector_service, "_connector_service", None)
    monkeypatch.setattr(settings_service, "SETTINGS_DIR", settings)
    monkeypatch.setattr(settings_service, "GLOBAL_SETTINGS_FILE", settings / "global.yaml")
    monkeypatch.setattr(settings_service, "PROJECTS_SETTINGS_DIR", settings / "projects")
    monkeypatch.setattr(settings_service, "_settings_service", None)

    yield tmp_path
    engine.dispose()
