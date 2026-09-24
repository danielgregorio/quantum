"""projects/tarefas: the UI Engine's proof app (U1), served end to end.

All in ui:*; the logic is the page's. The same .q becomes a console app (U3).
The app's content is Portuguese on purpose: an example app may show any
language (CODING.md).

What a person does in the app — create, finish, delete, edit, the sheet's cell
edits, the history — is tested in the app's own language, in
projects/tarefas/tests/tarefas.test.q and components/planilha.test.q, run by
`quantum test` (tests/apps/test_app_suites.py). What stays here is what those
tests cannot see: the HTML the UI Engine draws.
"""

import logging
import re
import shutil
from pathlib import Path

import pytest

from tests.apps.test_blog import page_text

TAREFAS = Path(__file__).resolve().parents[2] / "projects" / "tarefas"


@pytest.fixture
def app(tmp_path, monkeypatch):
    project = tmp_path / "tarefas"
    shutil.copytree(TAREFAS, project, ignore=shutil.ignore_patterns("data", "__pycache__"))
    monkeypatch.chdir(project)
    from quantum.cli.migrations import MigrationRunner
    assert [r["status"] for r in MigrationRunner(project).up()] == ["applied"]
    from quantum.runtime.web_server import QuantumWebServer
    logging.disable(logging.WARNING)
    flask_app = QuantumWebServer(str(project / "quantum.config.yaml")).app
    flask_app.config["TESTING"] = True
    yield flask_app.test_client(), project / "data" / "tarefas.db"
    logging.disable(logging.NOTSET)


def test_the_ui_layout_and_the_order(app):
    client, _ = app
    html = client.get("/").get_data(as_text=True)
    page = page_text(client.get("/"))
    assert page.index("Ler o guia do Quantum") < page.index("Instalar o Quantum")
    assert 'class="q-window"' in html and 'class="q-panel"' in html


def test_the_row_button_carries_the_id(app):
    client, _ = app
    html = client.get("/").get_data(as_text=True)
    forms = re.findall(r'<form method="post" class="q-action".*?</form>', html, re.S)
    assert any('value="alternar"' in f and 'name="id" value="1"' in f for f in forms)


def test_the_form_from_the_table_draws_the_fields_and_the_errors(app):
    # UI-10: fields and rules come from the schema; the form opens with the task's values
    client, _ = app
    assert '/tarefa/1' in client.get("/").get_data(as_text=True)          # the row's "Editar" link
    html = client.get("/tarefa/1").get_data(as_text=True)
    assert re.search(r'<input[^>]*value="Ler o guia do Quantum"[^>]*name="titulo"[^>]*required', html)
    assert '<option value="alta" selected>' in html and 'name="feita"' not in html   # columns= chooses
    client.post("/tarefa/1", data={"action": "salvar", "titulo": "", "prioridade": "urgente"},
                headers={"Referer": "http://localhost/tarefa/1"})
    errors = re.findall(r'q-field-error"[^>]*>\s*([^<]*?)\s*</span>', client.get("/tarefa/1").get_data(as_text=True))
    assert errors == ["Required", "Must be one of: baixa, media, alta"]


def test_the_sheet_sorts(app):
    # UI-13: the headers sort in the SQL
    client, _ = app
    html = client.get("/planilha?sort=titulo&dir=asc").get_data(as_text=True)
    order = re.findall(r'<input class="q-input" type="text" value="([^"]+)" name="value" required id="cell-titulo', html)
    assert order == sorted(order) and len(order) == 3


def test_schema_sql_is_what_the_migrations_produce():
    # DB-10: projects/tarefas keeps schema.sql and the migrations in step
    from quantum.cli.schema_plan import make_plan
    assert make_plan(TAREFAS / "schema.sql", TAREFAS / "migrations").steps == []
