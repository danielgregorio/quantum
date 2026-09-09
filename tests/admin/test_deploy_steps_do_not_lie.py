"""
The deploy pipeline reported success for work it never did.

_step_push slept 0.5s and reported "Image pushed to registry". _deploy_local
slept and reported "Local server started on http://localhost:8000".
_deploy_docker reported "Docker container running". _deploy_ssh reported
"Deployed to remote server". _step_health slept and reported "Health checks
passed: Application is healthy". Every one of them had a comment saying "in a
real implementation, we would…" — invisible from the screen, which showed a
green pipeline.

Someone reading that screen believes their application is live and healthy.
These tests pin the steps to failing honestly, and pin the health check —
which is just an HTTP GET, so it is now real — to actually requesting the URL.
"""

import pathlib
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

ADMIN = pathlib.Path(__file__).resolve().parents[2] / "quantum_admin"
for path in (str(ADMIN), str(ADMIN / "backend")):
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.deploy_service import (  # noqa: E402
    Deployment, DeployService, DeployStatus,
)


@pytest.fixture
def svc():
    return DeployService()


@pytest.fixture
def deployment(svc):
    # Built through create_deployment, because _update_step only writes into
    # steps that already exist — a Deployment with an empty step list
    # silently records nothing.
    d = svc.create_deployment(
        project_id=1, project_name="app", environment="local",
        branch="main", strategy="direct")
    d.status = DeployStatus.RUNNING
    return d


def step(deployment, name):
    for s in deployment.steps:
        if s.name == name:
            return s
    return None


class TestStepsThatDoNothingSaySo:
    def test_push_fails_instead_of_reporting_a_push(self, svc, deployment):
        assert svc._step_push(deployment) is False
        assert step(deployment, "push").status == "failed"
        assert "not implemented" in step(deployment, "push").message

    def test_local_deploy_does_not_claim_a_server_started(self, svc, deployment):
        assert svc._deploy_local(deployment) is False
        assert step(deployment, "deploy").status == "failed"
        assert "localhost:8000" not in deployment.logs

    def test_docker_deploy_does_not_claim_a_container_runs(self, svc, deployment):
        assert svc._deploy_docker(deployment) is False
        assert step(deployment, "deploy").status == "failed"

    def test_ssh_deploy_does_not_claim_a_remote_deploy(self, svc, deployment):
        assert svc._deploy_ssh(deployment) is False
        assert step(deployment, "deploy").status == "failed"

    def test_an_unknown_environment_fails(self, svc, deployment):
        deployment.environment = "kubernetes"
        assert svc._step_deploy(deployment) is False
        assert step(deployment, "deploy").status == "failed"

    def test_no_step_says_successful_without_doing_the_work(self, svc, deployment):
        svc._step_push(deployment)
        svc._deploy_docker(deployment)
        assert "successful" not in deployment.logs.lower()
        assert "healthy" not in deployment.logs.lower()


class HealthHandler(BaseHTTPRequestHandler):
    code = 200

    def do_GET(self):
        self.send_response(self.code)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


@pytest.fixture
def health_server():
    """A real HTTP server, so 'the health check ran' means it ran."""
    server = HTTPServer(("127.0.0.1", 0), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()


class TestTheHealthCheckIsReal:
    def test_it_passes_when_the_endpoint_answers(self, svc, deployment,
                                                 health_server, monkeypatch):
        port = health_server.server_address[1]
        monkeypatch.setattr(
            svc, "_health_url", lambda d: f"http://127.0.0.1:{port}/health")

        assert svc._step_health(deployment) is True
        assert step(deployment, "health").status == "completed"
        assert str(port) in step(deployment, "health").message

    def test_it_fails_when_nothing_is_listening(self, svc, deployment,
                                                monkeypatch):
        # Port 1 on loopback. The old code reported "Application is healthy"
        # for exactly this situation.
        monkeypatch.setattr(
            svc, "_health_url", lambda d: "http://127.0.0.1:1/health")

        assert svc._step_health(deployment, timeout=2) is False
        assert step(deployment, "health").status == "failed"
        assert "healthy" not in deployment.logs.lower()

    def test_it_fails_on_an_error_status(self, svc, deployment, health_server,
                                         monkeypatch):
        HealthHandler.code = 500
        try:
            port = health_server.server_address[1]
            monkeypatch.setattr(
                svc, "_health_url", lambda d: f"http://127.0.0.1:{port}/health")
            assert svc._step_health(deployment) is False
            assert step(deployment, "health").status == "failed"
        finally:
            HealthHandler.code = 200

    def test_no_url_configured_is_skipped_not_passed(self, svc, deployment,
                                                     monkeypatch):
        monkeypatch.setattr(svc, "_health_url", lambda d: None)

        assert svc._step_health(deployment) is True
        assert step(deployment, "health").status == "skipped"
        assert "nothing was checked" in deployment.logs
