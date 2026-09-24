"""projects/quantum-dashboard, end to end: migrations, the real server, actions.

Before, the POST was handled by a q:if at the top of the page (no validation,
and reloading repeated the operation), the database lived in /app/data and
starting depended on a startup.py that patched the framework at run time with
dead imports.
"""

import logging
import shutil
import sqlite3
from pathlib import Path

import pytest

from tests.apps.test_blog import page_text

DASHBOARD = Path(__file__).resolve().parents[2] / "projects" / "quantum-dashboard"


@pytest.fixture
def dashboard(tmp_path, monkeypatch):
    project = tmp_path / "dashboard"
    shutil.copytree(DASHBOARD, project, ignore=shutil.ignore_patterns("data", "logs", "__pycache__"))
    monkeypatch.chdir(project)
    from quantum.cli.migrations import MigrationRunner
    assert [r["status"] for r in MigrationRunner(project).up()] == ["applied"]
    from quantum.runtime.web_server import QuantumWebServer
    logging.disable(logging.WARNING)
    app = QuantumWebServer(str(project / "quantum.config.yaml")).app
    app.config["TESTING"] = True
    yield app.test_client(), project / "data" / "tasks.db"
    logging.disable(logging.NOTSET)


def rows(db, sql):
    return sqlite3.connect(db).execute(sql).fetchall()


def test_list_and_counters(dashboard):
    client, _ = dashboard
    page = page_text(client.get("/"))
    assert "3 Total tasks 2 Pending 1 Completed" in page
    assert page.index("Read the Quantum guide") < page.index("Install Quantum")   # pending first
    with client.get("/static/dashboard.css") as css:   # a file: close it
        assert css.status_code == 200


def test_filter(dashboard):
    client, _ = dashboard
    done = page_text(client.get("/?status=done"))
    assert "Install Quantum" in done and "Read the Quantum guide" not in done
    assert "No tasks here" in page_text(client.get("/?status=nothing"))


def test_create_validates_and_saves(dashboard):
    client, db = dashboard
    r = client.post("/", data={"action": "create", "title": "Write tests", "priority": "high"})
    assert r.status_code == 302
    assert "Task created: Write tests" in page_text(client.get("/"))
    assert ("Write tests", "high", "") in rows(db, "select title, priority, description from tasks")

    client.post("/", data={"action": "create", "title": "x"}, headers={"Referer": "http://localhost/"})
    assert "at least 3 characters" in page_text(client.get("/"))
    client.post("/", data={"action": "create", "title": "Strange priority", "priority": "urgent"},
                headers={"Referer": "http://localhost/"})
    assert rows(db, "select count(*) from tasks")[0][0] == 4


def test_complete_reopen_delete_go_back_to_the_filter(dashboard):
    client, db = dashboard
    r = client.post("/", data={"action": "markDone", "task_id": "1", "back": "pending"})
    assert r.headers["Location"].endswith("/?status=pending")
    assert rows(db, "select status from tasks where id = 1") == [("done",)]
    client.post("/", data={"action": "reopen", "task_id": "1"})
    assert rows(db, "select status from tasks where id = 1") == [("pending",)]
    client.post("/", data={"action": "delete", "task_id": "1", "back": "all"})
    assert rows(db, "select count(*) from tasks where id = 1") == [(0,)]
    assert "Task deleted." in page_text(client.get("/"))


def test_reloading_the_page_does_not_repeat_the_operation(dashboard):
    client, db = dashboard
    client.post("/", data={"action": "create", "title": "Only once"})
    client.get("/")
    client.get("/")
    assert rows(db, "select count(*) from tasks where title = 'Only once'") == [(1,)]
