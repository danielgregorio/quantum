"""
GET /datasources/{id}/logs answered every failure with 200 and a JSON `error`.

A client that checked the status — the admin's own logs modal among them —
took "Datasource with id 7 not found" or "Docker service is not available" for
a successful answer. Failures are HTTP errors now, with a `detail`: 404 for an
unknown datasource or a container that no longer exists, 409 for a datasource
with no container, 503 when Docker is not available or does not answer.
`?tail=` still says how many lines.
"""

import uuid

import pytest

from tests.admin.test_admin_smoke import app, auth, client, token  # noqa: F401  (fixtures)


@pytest.fixture
def datasource(app, client, auth):
    """A datasource row, with or without a container id."""
    project = client.post("/projects", json={"name": f"logs-{uuid.uuid4().hex[:8]}"}, headers=auth)
    assert project.status_code == 201, project.text
    db = next(app.get_db())
    created = []

    def make(container_id=None):
        row = app.crud.models.Datasource(
            project_id=project.json()["id"], name=f"ds-{uuid.uuid4().hex[:6]}",
            type="postgres", connection_type="docker", container_id=container_id)
        db.add(row)
        db.commit()
        created.append(row)
        return row.id

    yield make
    for row in created:
        db.delete(row)
    db.commit()
    db.close()


class FakeContainer:
    def __init__(self):
        self.tail = None

    def logs(self, tail, timestamps):
        self.tail = tail
        return b"line 1\nline 2\n"


class FakeDocker:
    """docker_service with a client whose containers.get does what the test says."""

    def __init__(self, get):
        self.client = type("Client", (), {})()
        self.client.containers = type("Containers", (), {"get": staticmethod(get)})()


class NotFound(Exception):
    """Named like docker.errors.NotFound, which is how the route recognises it."""


def test_an_unknown_datasource_is_404(client, auth):
    r = client.get("/datasources/987654/logs", headers=auth)
    assert r.status_code == 404 and "not found" in r.json()["detail"]


def test_a_datasource_without_a_container_is_409(client, auth, datasource):
    r = client.get(f"/datasources/{datasource()}/logs", headers=auth)
    assert r.status_code == 409 and "No container" in r.json()["detail"]


def test_without_docker_it_is_503(app, client, auth, datasource, monkeypatch):
    monkeypatch.setattr(app, "docker_service", None)
    r = client.get(f"/datasources/{datasource('abc123')}/logs", headers=auth)
    assert r.status_code == 503 and "not available" in r.json()["detail"]


def test_a_container_that_is_gone_is_404(app, client, auth, datasource, monkeypatch):
    def get(container_id):
        raise NotFound(container_id)
    monkeypatch.setattr(app, "docker_service", FakeDocker(get))
    r = client.get(f"/datasources/{datasource('abc123')}/logs", headers=auth)
    assert r.status_code == 404 and "no longer exists" in r.json()["detail"]


def test_docker_that_does_not_answer_is_503(app, client, auth, datasource, monkeypatch):
    def get(container_id):
        raise ConnectionError("connection refused")
    monkeypatch.setattr(app, "docker_service", FakeDocker(get))
    r = client.get(f"/datasources/{datasource('abc123')}/logs", headers=auth)
    assert r.status_code == 503 and "connection refused" in r.json()["detail"]


def test_the_logs_and_tail(app, client, auth, datasource, monkeypatch):
    container = FakeContainer()
    monkeypatch.setattr(app, "docker_service", FakeDocker(lambda container_id: container))
    r = client.get(f"/datasources/{datasource('abc123')}/logs?tail=7", headers=auth)
    assert r.status_code == 200
    assert r.json() == {"logs": "line 1\nline 2\n", "container_id": "abc123"}
    assert container.tail == 7


def test_the_logs_modal_reads_the_status(app):
    # The admin page's refreshLogs() used to look only for d.error in the body.
    page = open(app.__file__, encoding="utf-8").read()
    start = page.index("function refreshLogs(dsId)")
    script = page[start:page.index("function testDatasourceConnection", start)]
    assert "r.ok" in script and "d.detail" in script and "d.error" not in script
