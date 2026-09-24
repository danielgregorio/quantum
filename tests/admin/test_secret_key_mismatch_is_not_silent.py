"""A secret the current key cannot open is an error, not a value.

`decrypt_or_legacy` had an `except Exception: return stored` that applied to
both reasons for failing:

  1. the value was never encrypted (old rows, written when the
     `credentials_encrypted` column held plain JSON) — returning what was
     stored is right;
  2. the value IS a Fernet token and the current QUANTUM_ENCRYPTION_KEY does
     not open it (the key changed, was lost, or is missing on a new deploy,
     when the module falls back to the default key) — returning what was
     stored hands over the CIPHERTEXT as if it were the password.

Case 2 leaked in two ways: the connection tried to authenticate with the
token's base64 and the error pointed to "invalid password"; and the next save
encrypted that token again with the new key, destroying for good the password
only the old key could open — with nothing on the way saying so.
"""

import base64
import importlib
import os
import pathlib
import sys

import pytest

ADMIN = pathlib.Path(__file__).resolve().parents[2] / "quantum_admin"
for path in (str(ADMIN), str(ADMIN / "backend")):
    if path not in sys.path:
        sys.path.insert(0, path)

pytest.importorskip("cryptography", reason="the admin needs cryptography")


def _module_with_key(key):
    """Reload secret_manager with a given QUANTUM_ENCRYPTION_KEY.

    The cipher is built once in a module singleton, so changing the key needs a
    re-import — which is exactly what happens when the process starts with
    another environment variable.
    """
    previous = os.environ.get('QUANTUM_ENCRYPTION_KEY')
    if key is None:
        os.environ.pop('QUANTUM_ENCRYPTION_KEY', None)
    else:
        os.environ['QUANTUM_ENCRYPTION_KEY'] = key

    import secret_manager as sm
    sm.SecretManager._instance = None
    module = importlib.reload(sm)

    if previous is None:
        os.environ.pop('QUANTUM_ENCRYPTION_KEY', None)
    else:
        os.environ['QUANTUM_ENCRYPTION_KEY'] = previous
    return module


@pytest.fixture(autouse=True)
def _restore_singleton():
    yield
    import secret_manager as sm
    sm.SecretManager._instance = None
    importlib.reload(sm)


class TestChangedKey:
    def test_it_does_not_return_the_ciphertext_as_the_password(self):
        from cryptography.fernet import Fernet

        key_a = Fernet.generate_key().decode()
        key_b = Fernet.generate_key().decode()

        sm_a = _module_with_key(key_a)
        encrypted = sm_a.encrypt_value("the-real-password")

        sm_b = _module_with_key(key_b)
        with pytest.raises(ValueError) as error:
            sm_b.decrypt_or_legacy(encrypted)

        # Before: it returned `encrypted` — the token itself — as if it were the password.
        assert encrypted not in str(error.value)
        assert 'QUANTUM_ENCRYPTION_KEY' in str(error.value)

    def test_the_message_warns_that_saving_over_it_destroys_the_secret(self):
        from cryptography.fernet import Fernet

        sm_a = _module_with_key(Fernet.generate_key().decode())
        encrypted = sm_a.encrypt_value("secret")

        sm_b = _module_with_key(Fernet.generate_key().decode())
        with pytest.raises(ValueError) as error:
            sm_b.decrypt_or_legacy(encrypted)
        assert 'overwrite' in str(error.value).lower()


class TestTextNeverEncryptedStillPasses:
    """The legacy path must keep working — it is the reason it exists."""

    def test_plain_json_is_returned(self):
        from cryptography.fernet import Fernet
        sm = _module_with_key(Fernet.generate_key().decode())
        stored = '{"api_key": "abc123", "region": "us-east-1"}'
        assert sm.decrypt_or_legacy(stored) == stored

    def test_text_that_happens_to_be_valid_base64_is_returned(self):
        """`user:pass` decodes as base64? It does not matter: it does not start
        with 0x80 nor has 57 bytes, so it is not a Fernet token."""
        from cryptography.fernet import Fernet
        sm = _module_with_key(Fernet.generate_key().decode())
        for stored in ('abcd', 'password1234', base64.urlsafe_b64encode(
                b'x' * 60).decode()):
            assert sm.decrypt_or_legacy(stored) == stored

    def test_empty_passes_straight_through(self):
        from cryptography.fernet import Fernet
        sm = _module_with_key(Fernet.generate_key().decode())
        assert sm.decrypt_or_legacy('') == ''
        assert sm.decrypt_or_legacy(None) is None

    def test_the_right_key_opens_it_normally(self):
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        sm = _module_with_key(key)
        encrypted = sm.encrypt_value("ok")
        assert _module_with_key(key).decrypt_or_legacy(encrypted) == "ok"


class TestTokenDetection:
    def test_it_recognizes_a_fernet_token(self):
        from cryptography.fernet import Fernet
        sm = _module_with_key(Fernet.generate_key().decode())
        assert sm._looks_like_fernet_token(sm.encrypt_value("x")) is True

    def test_it_does_not_mistake_plain_text_for_a_token(self):
        from cryptography.fernet import Fernet
        sm = _module_with_key(Fernet.generate_key().decode())
        for text in ('password', '{"a": 1}', 'not-base64!!!', 'x' * 100):
            assert sm._looks_like_fernet_token(text) is False, text


class TestFailClosedInProduction:
    """Without QUANTUM_ENCRYPTION_KEY in production, the admin must not start.

    The default key is derived from literals in the source (a fixed password
    and salt, PBKDF2), so anyone with the code rebuilds it and decrypts
    everything. The admin writes encrypted values to quantum_admin/settings/*.yaml
    (versioned before), so the default RE-ARMS the leak on every save. In
    production that must be a refusal, not a warning nobody reads.
    """

    def _start(self, env, has_key):
        import subprocess
        e = dict(os.environ)
        e.pop('QUANTUM_ENCRYPTION_KEY', None)
        e.pop('QUANTUM_ADMIN_ENV', None)
        if env:
            e['QUANTUM_ADMIN_ENV'] = env
        if has_key:
            from cryptography.fernet import Fernet
            e['QUANTUM_ENCRYPTION_KEY'] = Fernet.generate_key().decode()
        root = str(pathlib.Path(__file__).resolve().parents[2])
        code = ("import sys; sys.path[:0]=[r'%s/quantum_admin', r'%s/quantum_admin/backend'];"
                "import secret_manager; secret_manager.SecretManager(); print('STARTED')" % (root, root))
        return subprocess.run([sys.executable, '-c', code], env=e,
                              capture_output=True, text=True)

    def test_production_without_a_key_refuses(self):
        r = self._start('production', has_key=False)
        assert 'STARTED' not in r.stdout
        assert 'requires QUANTUM_ENCRYPTION_KEY' in r.stderr, r.stderr[-200:]

    def test_production_with_a_key_starts(self):
        r = self._start('production', has_key=True)
        assert 'STARTED' in r.stdout, r.stderr[-200:]

    def test_development_without_a_key_starts_with_a_warning(self):
        r = self._start('development', has_key=False)
        assert 'STARTED' in r.stdout, r.stderr[-200:]
