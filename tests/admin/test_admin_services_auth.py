"""admin.auth.login: as credenciais do auth_service do backend, com bloqueio por tentativas."""

import pytest

from quantum_admin.services import auth

SENHA = "uma-senha-de-teste-suficientemente-longa"


@pytest.fixture(autouse=True)
def servico_novo(monkeypatch):
    from quantum_admin.backend import auth_service
    monkeypatch.setenv("ADMIN_PASSWORD", SENHA)
    monkeypatch.setenv("JWT_SECRET_KEY", "k" * 64)
    monkeypatch.setattr(auth_service, "_auth_service", None, raising=False)
    auth._reset()
    yield
    auth._reset()


def test_login_certo():
    r = auth.login("admin", SENHA)
    assert r["ok"] is True and r["username"] == "admin" and r["role"] == "admin" and r["expires_in_hours"] >= 1


@pytest.mark.parametrize("usuario,senha", [("admin", "errada"), ("fantasma", SENHA), ("", SENHA), ("admin", "")])
def test_falha_com_a_mesma_mensagem(usuario, senha):
    r = auth.login(usuario, senha)
    assert r == {"ok": False, "locked": False, "error": "invalid username or password"}


def test_bloqueia_depois_de_tentativas_seguidas_mesmo_com_a_senha_certa():
    for _ in range(auth.MAX_FALHAS):
        assert auth.login("admin", "chute")["ok"] is False
    r = auth.login("admin", SENHA)
    assert r["ok"] is False and r["locked"] is True and "try again" in r["error"]


def test_bloqueio_expira(monkeypatch):
    agora = [1000.0]
    monkeypatch.setattr(auth.time, "time", lambda: agora[0])
    for _ in range(auth.MAX_FALHAS):
        auth.login("admin", "chute")
    assert auth.login("admin", SENHA)["locked"] is True
    agora[0] += auth.JANELA + 1
    assert auth.login("admin", SENHA)["ok"] is True


def test_acerto_zera_as_falhas():
    for _ in range(auth.MAX_FALHAS - 1):
        auth.login("admin", "chute")
    assert auth.login("admin", SENHA)["ok"] is True
    assert auth.login("admin", "chute")["locked"] is False
