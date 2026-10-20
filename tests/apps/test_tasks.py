"""projects/tasks: the UI Engine's proof app (U1), served end to end.

All in ui:*; the logic is the page's. The same .q becomes a console app (U3).

What a person does in the app — create, finish, delete, edit, the sheet's cell
edits, the history — is tested in the app's own language, in
projects/tasks/tests/tasks.test.q and components/sheet.test.q, run by
`quantum test` (tests/apps/test_app_suites.py). What stays here is what those
tests cannot see: the HTML the UI Engine draws.
"""

import logging
import re
import shutil
from pathlib import Path

import pytest

from tests.apps.test_blog import page_text

TASKS = Path(__file__).resolve().parents[2] / "projects" / "tasks"


@pytest.fixture
def app(tmp_path, monkeypatch):
    project = tmp_path / "tasks"
    shutil.copytree(TASKS, project, ignore=shutil.ignore_patterns("data", "__pycache__"))
    monkeypatch.chdir(project)
    from quantum.cli.migrations import MigrationRunner
    assert [r["status"] for r in MigrationRunner(project).up()] == ["applied"]
    from quantum.runtime.web_server import QuantumWebServer
    logging.disable(logging.WARNING)
    flask_app = QuantumWebServer(str(project / "quantum.config.yaml")).app
    flask_app.config["TESTING"] = True
    yield flask_app.test_client(), project / "data" / "tasks.db"
    logging.disable(logging.NOTSET)


def test_the_ui_layout_and_the_order(app):
    client, _ = app
    html = client.get("/").get_data(as_text=True)
    page = page_text(client.get("/"))
    assert page.index("Read the Quantum guide") < page.index("Install Quantum")
    assert 'class="q-window"' in html and 'class="q-panel"' in html


def test_the_row_button_carries_the_id(app):
    client, _ = app
    html = client.get("/").get_data(as_text=True)
    forms = re.findall(r'<form method="post" class="q-action".*?</form>', html, re.S)
    assert any('value="toggle"' in f and 'name="id" value="1"' in f for f in forms)


def test_the_form_from_the_table_draws_the_fields_and_the_errors(app):
    # UI-10: fields and rules come from the schema; the form opens with the task's values
    client, _ = app
    assert '/task/1' in client.get("/").get_data(as_text=True)          # the row's "Edit" link
    html = client.get("/task/1").get_data(as_text=True)
    assert re.search(r'<input[^>]*value="Read the Quantum guide"[^>]*name="title"[^>]*required', html)
    assert '<option value="high" selected>' in html and 'name="done"' not in html   # columns= chooses
    client.post("/task/1", data={"action": "save", "title": "", "priority": "urgent"},
                headers={"Referer": "http://localhost/task/1"})
    errors = re.findall(r'q-field-error"[^>]*>\s*([^<]*?)\s*</span>', client.get("/task/1").get_data(as_text=True))
    assert errors == ["Required", "Must be one of: low, medium, high"]


def test_a_refused_task_comes_back_in_red(app):
    # ACT-2: the action refuses a title of two letters; the flash says why, as an error
    # (before: the page drew every flash in green)
    client, _ = app
    client.post("/", data={"action": "create", "title": "ab"}, headers={"Referer": "http://localhost/"})
    html = client.get("/").get_data(as_text=True)
    assert re.search(r'q-alert q-alert-danger.*?at least 3 characters', html, re.S)
    client.post("/", data={"action": "create", "title": "Water the plants"})
    assert 'q-alert q-alert-success' in client.get("/").get_data(as_text=True)


def test_the_sheet_sorts(app):
    # UI-13: the headers sort in the SQL
    client, _ = app
    html = client.get("/sheet?sort=title&dir=asc").get_data(as_text=True)
    order = re.findall(r'<input class="q-input" type="text" value="([^"]+)" name="value" required id="cell-title', html)
    assert order == sorted(order) and len(order) == 3


def test_schema_sql_is_what_the_migrations_produce():
    # DB-10: projects/tasks keeps schema.sql and the migrations in step
    from quantum.cli.schema_plan import make_plan
    assert make_plan(TASKS / "schema.sql", TASKS / "migrations").steps == []
