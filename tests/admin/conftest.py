"""Isolation of the admin services' tests (quantum_admin/services).

The services use the admin library, which has module paths and singletons:
the database (database.engine), settings/connectors.yaml (connector_service),
settings/global.yaml (settings_service). Without redirecting them all, a
connector test would write to the owner's real connectors.yaml.
"""

import hashlib
import pathlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

REAL_SETTINGS = pathlib.Path(__file__).resolve().parents[2] / "quantum_admin" / "settings"


def _fingerprint():
    if not REAL_SETTINGS.is_dir():
        return {}
    return {str(p.relative_to(REAL_SETTINGS)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(REAL_SETTINGS.rglob("*")) if p.is_file() and p.suffix in (".yaml", ".yml", ".json")}


@pytest.fixture(scope="session", autouse=True)
def real_settings_untouched():
    """The owner's data in quantum_admin/settings must not change because of the suite."""
    before = _fingerprint()
    yield
    after = _fingerprint()
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    assert not changed, f"the admin suite changed real data in quantum_admin/settings: {changed}"


@pytest.fixture
def isolated_admin(tmp_path, monkeypatch):
    from quantum_admin.core import connector_service, database, settings_service
    from quantum_admin.services import _base

    engine = create_engine(f"sqlite:///{(tmp_path / 'admin.db').as_posix()}",
                           connect_args={"check_same_thread": False})
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    monkeypatch.setattr(_base, "_initialized", False)

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
