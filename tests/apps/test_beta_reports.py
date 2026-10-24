"""projects/beta-reports: where the games' beta reports land (PLAN_PANDAFOOT.md, "The beta's reports").

A report posted to /api/reports is kept in SQLite and told to the forge: the save as a file of the
repository's branch, the report as an issue with its labels. The forge is a real HTTP server in the test
(FakeForge, GitHub's shape); the token comes from the environment (INV-3) and is what the forge receives.
"""

import base64
import json
import logging
import shutil
import sqlite3
import threading
from pathlib import Path

import pytest
from werkzeug.serving import make_server
from werkzeug.wrappers import Request, Response

PROJECT = Path(__file__).resolve().parents[2] / "projects" / "beta-reports"

REPORT = {"game": "pandafoot", "version": "2.1", "kind": "bug", "text": "The table froze after round 18.",
          "screen": "standings", "option": "Lontra AC",
          "context": "world 7, season 2026, round 18/18; Ana at Lontra AC (division 4)",
          "player": "Fernando", "save": json.dumps({"season": 2026, "matchday": 18, "club": "Lontra AC"})}


class FakeForge:
    """GitHub's contents and issues APIs over real HTTP; keeps what it received. down=True answers 503."""

    def __init__(self):
        self.received = []                   # (method, path, headers, json body)
        self.down = False
        self.server = make_server("127.0.0.1", 0, self.app, threaded=True)
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()

    @Request.application
    def app(self, request):
        body = json.loads(request.data) if request.data else None
        self.received.append((request.method, request.path, dict(request.headers), body))
        if self.down:
            return Response('{"message": "Service Unavailable"}', status=503, content_type="application/json")
        if request.method == "POST" and request.path == "/repos/acme/beta/issues":
            number = 40 + sum(1 for m, p, _, _ in self.received if m == "POST" and p == request.path)
            return Response(json.dumps({"number": number, "html_url": f"https://forge.test/acme/beta/issues/{number}"}),
                            status=201, content_type="application/json")
        if request.method == "PUT" and request.path.startswith("/repos/acme/beta/contents/"):
            return Response(json.dumps({"content": {"path": request.path.split("/contents/")[1]}}),
                            status=201, content_type="application/json")
        return Response('{"message": "Not Found"}', status=404, content_type="application/json")


@pytest.fixture
def forge():
    with FakeForge() as server:
        yield server


@pytest.fixture
def receiver(tmp_path, monkeypatch, forge):
    project = tmp_path / "beta-reports"
    shutil.copytree(PROJECT, project, ignore=shutil.ignore_patterns("data", ".quantum", "__pycache__"))
    monkeypatch.chdir(project)
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    from quantum.cli.migrations import MigrationRunner
    assert [r["status"] for r in MigrationRunner(project).up()] == ["applied"]
    with sqlite3.connect(project / "data" / "reports.db") as db:     # the forge of the test
        db.execute("UPDATE settings SET forge = ?, repo = 'acme/beta'", (forge.url,))
    from quantum.runtime.web_server import QuantumWebServer
    logging.disable(logging.WARNING)
    app = QuantumWebServer(str(project / "quantum.config.yaml")).app
    app.config["TESTING"] = True
    yield app.test_client(), project
    logging.disable(logging.NOTSET)


def rows(project):
    with sqlite3.connect(project / "data" / "reports.db") as db:
        db.row_factory = sqlite3.Row
        return [dict(r) for r in db.execute("SELECT * FROM reports ORDER BY id")]


def test_a_report_is_kept_its_save_stored_and_an_issue_opened(receiver, forge):
    client, project = receiver
    response = client.post("/api/reports", json=REPORT)
    assert response.status_code == 201 and response.get_json() == {"number": 1}
    kept, = rows(project)
    assert {k: kept[k] for k in REPORT} == REPORT and kept["issue"] == 41

    (put_method, put_path, put_headers, put_body), (issue_method, issue_path, issue_headers, issue) = forge.received
    assert (put_method, put_path) == ("PUT", "/repos/acme/beta/contents/beta-reports/pandafoot/1.json")
    assert base64.b64decode(put_body["content"]).decode() == REPORT["save"]
    assert put_body["branch"] == "beta-reports" and put_headers["Authorization"] == "Bearer test-token"
    assert (issue_method, issue_path) == ("POST", "/repos/acme/beta/issues")
    assert issue["title"] == "[pandafoot 2.1] bug: The table froze after round 18."
    assert issue["labels"] == ["beta-report", "pandafoot", "bug"]
    assert "> The table froze after round 18." in issue["body"]
    assert "world 7, season 2026" in issue["body"] and "Fernando" in issue["body"] and "Lontra AC" in issue["body"]
    assert "`beta-reports/pandafoot/1.json` on the branch `beta-reports`" in issue["body"]
    assert issue_headers["Authorization"] == "Bearer test-token"


def test_without_a_save_only_the_issue(receiver, forge):
    client, project = receiver
    report = dict(REPORT, save="", kind="suggestion", text="A cup for the 4th division only.")
    assert client.post("/api/reports", json=report).get_json() == {"number": 1}
    assert [(m, p) for m, p, _, _ in forge.received] == [("POST", "/repos/acme/beta/issues")]
    assert "save" not in forge.received[0][3]["body"].lower()


def test_the_forge_down_the_report_is_kept_all_the_same(receiver, forge):
    client, project = receiver
    forge.down = True
    assert client.post("/api/reports", json=REPORT).status_code == 201
    kept, = rows(project)
    assert kept["text"] == REPORT["text"] and kept["issue"] is None      # told later, by hand or a retry


def test_without_the_token_the_report_is_kept_and_nothing_is_sent(receiver, forge, monkeypatch):
    client, project = receiver
    monkeypatch.delenv("GITHUB_TOKEN")
    assert client.post("/api/reports", json=REPORT).status_code == 201
    assert forge.received == [] and rows(project)[0]["issue"] is None


def test_what_is_refused(receiver, forge):
    client, project = receiver
    bad = client.post("/api/reports", json=dict(REPORT, kind="rant", text="x"))
    assert bad.status_code == 422 and set(bad.get_json()["fields"]) == {"kind", "text"}
    assert client.post("/api/reports", json=dict(REPORT, game="Panda Foot!")).status_code == 422
    other = client.post("/api/reports", json=REPORT, headers={"Origin": "https://evil.example"})
    assert other.status_code == 403
    game = client.post("/api/reports", json=REPORT, headers={"Origin": "https://quantumframework.net"})
    assert game.status_code == 201
    assert game.headers["Access-Control-Allow-Origin"] == "https://quantumframework.net"
    assert len(rows(project)) == 1 and len(forge.received) == 2


def test_twenty_an_hour_from_one_player(receiver, forge):
    client, _ = receiver
    report = dict(REPORT, save="")
    for _ in range(20):
        assert client.post("/api/reports", json=report, headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 201
    assert client.post("/api/reports", json=report, headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 429
    assert client.post("/api/reports", json=report, headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 201
