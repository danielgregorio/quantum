"""
An unconfigured webhook accepted anyone, and a push event starts a deploy.

verify_github_signature returned True when GITHUB_WEBHOOK_SECRET was unset —
"skipping verification" — and verify_gitlab_token did the same. Unset is the
state of every default install, so POST /webhooks/github with
X-GitHub-Event: push and no signature reached process_github_push, which
creates a deployment. Anyone able to reach the port could deploy.

Unconfigured now means refused. A webhook that does nothing is a missing
feature; one that trusts everybody is a way in.
"""

import hashlib
import hmac
import pathlib
import sys

import pytest

ADMIN = pathlib.Path(__file__).resolve().parents[2] / "quantum_admin"
for path in (str(ADMIN), str(ADMIN / "backend")):
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.webhook_service import WebhookService  # noqa: E402


def service(github_secret="", gitlab_token=""):
    """A WebhookService with only the fields these checks touch.

    Built without __init__ on purpose: the constructor wants a database
    session, and signature verification does not.
    """
    svc = WebhookService.__new__(WebhookService)
    svc.github_secret = github_secret
    svc.gitlab_token = gitlab_token
    return svc


def sign(secret, payload):
    return "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256).hexdigest()


class TestGitHub:
    def test_unconfigured_refuses_an_unsigned_payload(self):
        assert service().verify_github_signature(b'{"ref":"main"}', "") is False

    def test_unconfigured_refuses_even_a_well_formed_signature(self):
        # The attacker can sign with anything; without a configured secret
        # there is nothing to check it against.
        payload = b'{"ref":"main"}'
        assert service().verify_github_signature(
            payload, sign("o-que-o-atacante-quiser", payload)) is False

    def test_configured_accepts_the_right_signature(self):
        payload = b'{"ref":"refs/heads/main"}'
        svc = service(github_secret="segredo-de-verdade")
        assert svc.verify_github_signature(
            payload, sign("segredo-de-verdade", payload)) is True

    def test_configured_rejects_a_wrong_signature(self):
        payload = b'{"ref":"refs/heads/main"}'
        svc = service(github_secret="segredo-de-verdade")
        assert svc.verify_github_signature(
            payload, sign("segredo-errado", payload)) is False

    def test_configured_rejects_a_missing_signature(self):
        svc = service(github_secret="segredo-de-verdade")
        assert svc.verify_github_signature(b"{}", "") is False

    def test_the_payload_is_what_is_signed(self):
        svc = service(github_secret="segredo-de-verdade")
        signature = sign("segredo-de-verdade", b'{"ref":"main"}')
        assert svc.verify_github_signature(b'{"ref":"OUTRO"}', signature) is False


class TestGitLab:
    def test_unconfigured_refuses_an_empty_token(self):
        assert service().verify_gitlab_token("") is False

    def test_unconfigured_refuses_any_token(self):
        assert service().verify_gitlab_token("qualquer-coisa") is False

    def test_configured_accepts_the_right_token(self):
        assert service(gitlab_token="t0ken").verify_gitlab_token("t0ken") is True

    def test_configured_rejects_a_wrong_token(self):
        assert service(gitlab_token="t0ken").verify_gitlab_token("outro") is False
