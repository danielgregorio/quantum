"""`quantum admin` (quantum/cli/admin.py): the generated config, data in the given folder, screens served."""

import argparse
import sys

import pytest
import yaml

from quantum.cli import admin as cmd

PASSWORD = "a-test-password-that-is-long-enough"


@pytest.fixture
def environment(monkeypatch):
    # prepare() writes to os.environ; monkeypatch gives the values back at the end.
    for name in ("QUANTUM_ADMIN_DATABASE_URL", "QUANTUM_ADMIN_SETTINGS_DIR",
                 "QUANTUM_ADMIN_ROOT", "JWT_SECRET_KEY"):
        monkeypatch.setenv(name, "x")
        monkeypatch.delenv(name)


def test_the_config_points_to_the_data_folder(tmp_path, environment):
    import os
    config = cmd.prepare(str(tmp_path / "data"), str(tmp_path), 8091)
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    assert config.parent == (tmp_path / "data").resolve()
    assert (cmd.screens_folder() / "admin" / "login.q").is_file()
    assert data["paths"]["components"] == cmd.screens_folder().as_posix()
    assert (cmd.assets_folder() / "quantum-admin.css").is_file()
    assert data["paths"]["static"] == cmd.assets_folder().as_posix()
    assert data["server"] == {"host": "127.0.0.1", "port": 8091, "reload": False, "debug": False}
    assert data["security"]["login_url"] == "/admin/login"
    assert data["services"] == cmd.MODULES
    assert os.environ["QUANTUM_ADMIN_DATABASE_URL"].endswith("data/quantum_admin.db")
    assert os.environ["QUANTUM_ADMIN_SETTINGS_DIR"] == str(config.parent / "settings")
    assert os.environ["QUANTUM_ADMIN_ROOT"] == str(tmp_path.resolve())


def test_keys_survive_a_restart(tmp_path, environment):
    # Without this, every session dropped on each `quantum admin`.
    first = yaml.safe_load(cmd.prepare(str(tmp_path), ".", 8090).read_text(encoding="utf-8"))
    second = yaml.safe_load(cmd.prepare(str(tmp_path), ".", 8090).read_text(encoding="utf-8"))
    assert len(first["security"]["secret_key"]) == 64
    assert first["security"]["secret_key"] == second["security"]["secret_key"]


def test_without_the_extra_it_says_how_to_install(monkeypatch, capsys, tmp_path):
    monkeypatch.setitem(sys.modules, "jwt", None)
    args = argparse.Namespace(data=str(tmp_path / "d"), root=".", port=8090)
    assert cmd.handle_admin(args) == 1
    assert 'pip install "quantum-framework[admin]"' in capsys.readouterr().out
    assert not (tmp_path / "d").exists()


def test_the_server_of_the_generated_config_serves_the_screens(tmp_path, environment, isolated_admin, monkeypatch):
    import logging
    from quantum import services
    from quantum.runtime.web_server import QuantumWebServer
    from quantum_admin.core import auth_service

    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setattr(auth_service, "_auth_service", None)
    services._reset()
    config = cmd.prepare(str(tmp_path / "data"), str(isolated_admin), 8090)
    logging.disable(logging.CRITICAL)
    try:
        client = QuantumWebServer(str(config)).app.test_client()
        assert client.get("/admin").status_code in (302, 303)
        assert "/admin/login" in client.get("/admin").headers["Location"]
        assert client.get("/admin/login").status_code == 200
        with client.get("/static/quantum-admin.css") as css:   # a file: close it
            assert "qa-login" in css.get_data(as_text=True)
        wrong = client.post("/admin/login", data={"action": "signIn", "username": "admin", "password": "wrong"})
        assert wrong.headers["Location"].endswith("/admin/login")
        assert client.get("/admin").status_code in (302, 303)
        right = client.post("/admin/login", data={"action": "signIn", "username": "admin", "password": PASSWORD})
        assert right.headers["Location"].endswith("/admin/applications")
        assert client.get("/admin").status_code == 200
    finally:
        logging.disable(logging.NOTSET)
        services._reset()
