"""admin.auth.login: the admin library's auth_service credentials, with a lock after repeated attempts."""

import pytest

from quantum_admin.services import auth

PASSWORD = "a-test-password-that-is-long-enough"


@pytest.fixture(autouse=True)
def new_service(monkeypatch):
    from quantum_admin.core import auth_service
    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setenv("JWT_SECRET_KEY", "k" * 64)
    monkeypatch.setattr(auth_service, "_auth_service", None, raising=False)
    auth._reset()
    yield
    auth._reset()


def test_a_right_login():
    r = auth.login("admin", PASSWORD)
    assert r["ok"] is True and r["username"] == "admin" and r["role"] == "admin" and r["expires_in_hours"] >= 1


@pytest.mark.parametrize("user,password", [("admin", "wrong"), ("ghost", PASSWORD), ("", PASSWORD), ("admin", "")])
def test_it_fails_with_the_same_message(user, password):
    r = auth.login(user, password)
    assert r == {"ok": False, "locked": False, "error": "invalid username or password"}


def test_it_locks_after_repeated_attempts_even_with_the_right_password():
    for _ in range(auth.MAX_FAILURES):
        assert auth.login("admin", "guess")["ok"] is False
    r = auth.login("admin", PASSWORD)
    assert r["ok"] is False and r["locked"] is True and "try again" in r["error"]


def test_the_lock_expires(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(auth.time, "time", lambda: now[0])
    for _ in range(auth.MAX_FAILURES):
        auth.login("admin", "guess")
    assert auth.login("admin", PASSWORD)["locked"] is True
    now[0] += auth.WINDOW + 1
    assert auth.login("admin", PASSWORD)["ok"] is True


def test_a_success_clears_the_failures():
    for _ in range(auth.MAX_FAILURES - 1):
        auth.login("admin", "guess")
    assert auth.login("admin", PASSWORD)["ok"] is True
    assert auth.login("admin", "guess")["locked"] is False
