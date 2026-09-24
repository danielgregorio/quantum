"""projects/tarefas in the console (UI-3): the same .q, the same script as the browser.

The console renderer (quantum/runtime/ui_console.py) asks the application's
server for the view tree and sends the same actions the browser sends.
"""

import asyncio
import logging
import shutil
import threading
from pathlib import Path

import pytest

from tests.console_pilot import page_loaded, press

TAREFAS = Path(__file__).resolve().parents[2] / "projects" / "tarefas"


@pytest.fixture
def url(tmp_path, monkeypatch):
    project = tmp_path / "tarefas"
    shutil.copytree(TAREFAS, project, ignore=shutil.ignore_patterns("data", "__pycache__"))
    monkeypatch.chdir(project)
    from quantum.cli.migrations import MigrationRunner
    MigrationRunner(project).up()
    from werkzeug.serving import make_server
    from quantum.runtime.web_server import QuantumWebServer
    logging.disable(logging.WARNING)
    app = QuantumWebServer(str(project / "quantum.config.yaml")).app
    server = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/"
    server.shutdown()
    logging.disable(logging.NOTSET)


def screen_text(app) -> str:
    from textual.widgets import Button, Static
    parts = [str(w.render()) for w in app.query(Static)]
    parts += [str(b.label) for b in app.query(Button)]
    return " | ".join(parts)


def run_console(url, width, script):
    from quantum.runtime.ui_console import ConsoleUI

    async def main():
        app = ConsoleUI(url)
        async with app.run_test(size=(width, 50)) as pilot:
            await page_loaded(app, pilot)
            await script(app, pilot)

    asyncio.run(main())


def test_summary_and_list(url):
    # UI-3
    async def script(app, pilot):
        text = screen_text(app)
        assert "Total: 3" in text and "Abertas: 2" in text and "Feitas: 1" in text
        assert "Ler o guia do Quantum" in text and "Escrever a primeira página" in text
        assert app.title == "Tarefas"
    run_console(url, 140, script)


def test_complete_with_the_row_button(url):
    # UI-3: the button sends the q:action with the row's id, as in the browser
    from textual.widgets import Button

    async def script(app, pilot):
        complete = [b for b in app.query(Button) if str(b.label) == "Concluir"][0]
        await press(app, pilot, complete)
        text = screen_text(app)
        assert "Feitas: 2" in text and "Abertas: 1" in text
    run_console(url, 140, script)


def test_create_through_the_form_and_validate(url):
    # UI-3: the form sends the fields; validation and flash are the web's
    from textual.widgets import Button, Input

    async def script(app, pilot):
        app.query_one(Input).value = "Criada pelo console"
        await press(app, pilot, [b for b in app.query(Button) if str(b.label) == "Criar"][0])
        assert "Criada: Criada pelo console" in screen_text(app) and "Total: 4" in screen_text(app)
        app.query_one(Input).value = "x"
        await press(app, pilot, [b for b in app.query(Button) if str(b.label) == "Criar"][0])
        assert "at least 3 characters" in screen_text(app)
    run_console(url, 140, script)


def test_a_narrow_terminal_stacks(url):
    # UI-2 in the console: stack-below="md" stacks below 96 columns
    from textual.containers import Horizontal, Vertical

    async def script(app, pilot):
        assert isinstance(app.query_one("#principal"), Vertical)
        assert app.query_one("#lateral").size.width > 50          # stacked: full width
    run_console(url, 70, script)

    async def wide(app, pilot):
        assert isinstance(app.query_one("#principal"), Horizontal)
        assert app.query_one("#lateral").size.width == 260 // 8  # width="260" in columns
    run_console(url, 140, wide)
