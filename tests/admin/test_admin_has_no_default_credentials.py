"""
The admin shipped with credentials published in its own source.

`auth_service.py` signed JWTs with "quantum-admin-secret-change-in-production"
and set the admin password to "admin" when the env vars were unset — which is
the state of every fresh install. Both are readable in the repository, so an
unconfigured admin gave full access two independent ways: log in with
admin/admin, or skip the login entirely and present a token forged with the
published key.

This pins both shut, and pins the development path open: an unconfigured
admin still runs, with values that are random per process.
"""

import pathlib
import sys
import time

import pytest

ADMIN = pathlib.Path(__file__).resolve().parents[2] / "quantum_admin"
if str(ADMIN) not in sys.path:
    sys.path.insert(0, str(ADMIN))

jwt = pytest.importorskip("jwt", reason="PyJWT not installed")

from backend.auth_service import AuthService, AuthConfigError  # noqa: E402

PUBLISHED_SECRET = "quantum-admin-secret-change-in-production"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("JWT_SECRET_KEY", "ADMIN_PASSWORD", "QUANTUM_ADMIN_ENV"):
        monkeypatch.delenv(var, raising=False)


def forge(secret, username="admin", role="admin"):
    """A token an attacker builds from the published key. No login involved."""
    return jwt.encode(
        {
            "sub": "1", "user_id": 1, "username": username, "role": role,
            "exp": int(time.time()) + 3600, "iat": int(time.time()),
        },
        secret,
        algorithm="HS256",
    )


class TestTheForgedTokenIsRejected:
    def test_a_token_signed_with_the_published_key_is_refused(self):
        svc = AuthService()
        assert svc.verify_token(forge(PUBLISHED_SECRET)) is None

    def test_the_signing_key_is_not_the_published_one(self):
        assert AuthService().secret_key != PUBLISHED_SECRET

    def test_two_processes_do_not_share_a_guessable_key(self):
        # Random per process. The cost (sessions do not survive a restart) is
        # why production mode demands a real key — see below.
        assert AuthService().secret_key != AuthService().secret_key

    def test_setting_the_published_key_explicitly_is_refused(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", PUBLISHED_SECRET)
        with pytest.raises(AuthConfigError, match="forge"):
            AuthService()

    def test_a_real_key_is_used_as_given(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "d5f1" * 16)
        assert AuthService().secret_key == "d5f1" * 16


class TestTheDefaultPasswordIsGone:
    def test_admin_admin_does_not_log_in(self):
        assert AuthService().authenticate("admin", "admin") is None

    def test_other_obvious_passwords_do_not_log_in(self):
        svc = AuthService()
        for guess in ("password", "changeme", "123456", "quantum", ""):
            assert svc.authenticate("admin", guess) is None, guess

    def test_setting_admin_as_the_password_is_refused(self, monkeypatch):
        monkeypatch.setenv("ADMIN_PASSWORD", "admin")
        with pytest.raises(AuthConfigError):
            AuthService()

    def test_a_configured_password_works(self, monkeypatch):
        monkeypatch.setenv("ADMIN_PASSWORD", "uma-senha-longa-de-verdade")
        svc = AuthService()
        assert svc.authenticate("admin", "uma-senha-longa-de-verdade")

    def test_the_generated_password_is_reported_and_works(self):
        svc = AuthService()
        assert svc.generated_password, "a login nobody can read is no login"
        assert svc.authenticate("admin", svc.generated_password)

    def test_each_instance_gets_its_own_password(self):
        # DEFAULT_USERS is a class attribute and was shallow-copied, so the
        # first instance wrote its hash onto the class and every later one
        # inherited it — a changed ADMIN_PASSWORD had no effect.
        a, b = AuthService(), AuthService()
        assert a.authenticate("admin", a.generated_password)
        assert b.authenticate("admin", a.generated_password) is None

    def test_the_class_default_stays_unset(self):
        AuthService()
        assert AuthService.DEFAULT_USERS["admin"]["password_hash"] is None


class TestProductionRefusesToGuess:
    def test_production_without_a_key_does_not_boot(self, monkeypatch):
        monkeypatch.setenv("QUANTUM_ADMIN_ENV", "production")
        monkeypatch.setenv("ADMIN_PASSWORD", "uma-senha-longa-de-verdade")
        with pytest.raises(AuthConfigError, match="JWT_SECRET_KEY"):
            AuthService()

    def test_production_without_a_password_does_not_boot(self, monkeypatch):
        monkeypatch.setenv("QUANTUM_ADMIN_ENV", "production")
        monkeypatch.setenv("JWT_SECRET_KEY", "d5f1" * 16)
        with pytest.raises(AuthConfigError, match="ADMIN_PASSWORD"):
            AuthService()

    def test_production_fully_configured_boots(self, monkeypatch):
        monkeypatch.setenv("QUANTUM_ADMIN_ENV", "production")
        monkeypatch.setenv("JWT_SECRET_KEY", "d5f1" * 16)
        monkeypatch.setenv("ADMIN_PASSWORD", "uma-senha-longa-de-verdade")
        svc = AuthService()
        assert svc.authenticate("admin", "uma-senha-longa-de-verdade")


class TestDevelopmentStillWorks:
    def test_an_unconfigured_admin_still_starts(self):
        # The fix must not turn "no config" into "cannot run locally".
        svc = AuthService()
        session = svc.authenticate("admin", svc.generated_password)
        assert session, "the generated password must actually log in"

        token = session.get("token") or session.get("access_token")
        assert token, f"authenticate() returned no token: {sorted(session)}"
        assert svc.verify_token(token) is not None
