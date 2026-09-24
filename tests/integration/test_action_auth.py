"""
Integration tests for q:action + session-based authentication.

Regression coverage for the bug found in the 2026-09 audit (see FULL_AUDIT_2026-09.md,
Cluster D): ActionHandler called ExecutionContext.resolve_expression()/evaluate_condition(),
methods that never existed, so any q:action with q:set/q:if crashed. The exception was
then returned as (referrer, 500) and redirect()'d, disguising a server error as a
successful redirect. Separately, ActionHandler created a fresh, empty ExecutionContext per
request instead of reusing the Flask session, so even a working q:set could never persist
login state.

These tests exercise the real Flask app + examples/test-auth-login.q and
examples/test-auth-protected.q end to end — no mocks — because that is exactly the
boundary the original bugs lived in and unit tests with mocked services did not catch.
"""

import pytest
from pathlib import Path
from quantum.runtime.web_server import QuantumWebServer

# Absolute path — some other test in the full suite changes the process cwd
# without restoring it, so a relative "./examples" here is not reliable
# (confirmed: this fixture 404'd every route when run as part of `pytest tests/`
# despite passing in isolation or with just `pytest tests/integration/`).
EXAMPLES_DIR = (Path(__file__).resolve().parent.parent.parent / "examples").as_posix()


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    """Flask test client pointed at examples/, where the auth test components live."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
server:
  debug: true
paths:
  components: {EXAMPLES_DIR}
  static: ./static
  logs: ./logs
logging:
  level: ERROR
  console: false
  file: false
""",
        encoding="utf-8",
    )
    server = QuantumWebServer(str(config_path))
    server.app.config['TESTING'] = True
    with server.app.test_client() as client:
        yield client


class TestActionAuthFlow:
    """End-to-end login flow through q:action + session scope."""

    def test_protected_route_redirects_when_unauthenticated(self, auth_client):
        response = auth_client.get('/test-auth-protected')
        assert response.status_code == 302
        assert response.headers['Location'] == '/login'

    def test_login_action_does_not_crash(self, auth_client):
        """q:set inside q:action used to raise AttributeError on every call."""
        response = auth_client.post(
            '/test-auth-login',
            data={'email': 'user@test.com', 'password': 'secret'},
        )
        assert response.status_code == 200

    def test_login_persists_session_across_requests(self, auth_client):
        """The core bug: session mutations made inside an action never reached
        Flask's session, so the very next request still looked unauthenticated."""
        auth_client.post(
            '/test-auth-login',
            data={'email': 'user@test.com', 'password': 'secret'},
        )
        response = auth_client.get('/test-auth-protected')
        assert response.status_code == 200

    def test_action_error_is_a_real_error_not_a_disguised_redirect(self, tmp_path):
        """A failing action must return a visible error, never a 500 wrapped in
        a redirect Response (which most clients read as success)."""
        components_dir = tmp_path / "examples"
        components_dir.mkdir()
        (components_dir / "broken_action.q").write_text(
            """<q:component name="BrokenAction">
  <q:action name="boom" method="POST">
    <q:set name="counter" value="not_a_number" type="integer" />
  </q:action>
  unreachable
</q:component>
""",
            encoding="utf-8",
        )
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            f"""
server:
  debug: true
paths:
  components: {components_dir.as_posix()}
  static: ./static
  logs: ./logs
logging:
  level: ERROR
  console: false
  file: false
""",
            encoding="utf-8",
        )
        server = QuantumWebServer(str(config_path))
        server.app.config['TESTING'] = True
        with server.app.test_client() as client:
            response = client.post('/broken_action', data={})

        assert response.status_code == 500
        assert 'Location' not in response.headers
