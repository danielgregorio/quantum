"""The Kanban in each of its versions, by one parameter (UI-18, PLAN_PLATFORMS.md Phase 2).

`quantum run <app> --on web|desktop|terminal` runs projects/kanban; the same SCRIPT — sign in, a card
added, moved and done (the webhook told), the AI's subtasks, its agent and its streamed summary, issues
imported from a forge, a viewer who changes nothing — runs in each, through the drivers of
tests/apps/ui_drivers.py. A feature that fails in one version fails its test. The forge and the model
are real HTTP servers in the test (tests/apps/test_kanban.py, tests/fake_ollama.py).
"""

import asyncio
import importlib.util
import json
import logging
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import types

import pytest
import requests

from tests.apps.test_kanban import KANBAN, FakeForge
from tests.apps.ui_drivers import Browser, run_console_script, run_script
from tests.fake_ollama import FakeOllama

HAS_RAG = importlib.util.find_spec("chromadb") is not None


def sign_in(who):
    return [("visit", "/login"), ("fill", "email", f"{who}@example.com"), ("fill", "password", "kanban-demo"),
            ("click", "Sign in")]


SCRIPT = sign_in("bruno") + [
    ("sees", ["Bruno (member)", "Website launch", "6 cards"]),
    ("follow", "Open Website launch"),
    ("sees", ["To do 2", "Doing 2/3", "Review 1/2", "Done 1", "Write the about page", "Set up the domain"]),
    # a card added, moved to the end; the board's webhook is told when it is done
    ("fill", "title", "Write the FAQ"),
    ("click", "Add a card"),
    ("sees", ["Card added: Write the FAQ", "To do 3"]),
    # UI-19: the page slides in, the flash fades in, the new card opens in place — the same in every version
    ("motions", [("slide", "normal", "page"), ("fade", "normal", "alert"), ("expand", "normal", "card")]),
    ("click_in", "Write the FAQ", "▶"),
    ("sees", ["Doing 3/3"]),
    ("motions", [("slide", "normal", "page"), ("slide", "normal", "card")]),
    ("click_in", "Write the FAQ", "▶"),
    ("click_in", "Write the FAQ", "▶"),
    ("sees", ["Done 2"]),
    # the AI splits a card into subtasks
    ("follow_in", "Write the about page", "Open"),
    ("sees", ["#1 Write the about page", "History"]),
    ("click", "Split it with the AI"),
    ("sees", ["3 subtasks of Write the about page added.", "Pick the photo", "Ask Ana to review"]),
    # the agent says what is late, with the tool it used
    ("tab", "Ask"),
    ("motions", [("slide", "normal", "page"), ("fade", "normal", "alert"), ("expand", "normal", "tab:Ask")]),
    ("follow", "Ask the agent"),
    ("sees", ["Set up the domain is late; Ana has it.", "late_cards()"]),
] + ([
    # the board answers from its own cards, with the cards it comes from
    ("fill", "question", "Who has the domain?"),
    ("click", "Ask"),
    ("sees", ["Ana has the domain [1].", "Set up the domain (Doing, Ana"]),
] if HAS_RAG else []) + [
    # the summary is written as it is read
    ("follow", "Summarise the board"),
    ("waits_for", "the domain is late"),
    # a repository's issues become cards, each once
    ("tab", "Settings"),
    ("fill", "repository", "acme/site"),
    ("click", "Import"),
    ("sees", ["2 issues of acme/site imported.", "Dark mode", "Search box"]),
    ("visit", "/board/1?tab=Flow"),
    ("sees", ["Done: 2, in"]),
    # a viewer reads and changes nothing
    ("follow", "Sign out"),
    ("click", "Sign out"),
    ("sees", ["Signed out."]),
] + sign_in("carla") + [
    ("follow", "Open Website launch"),
    ("sees", ["Carla (viewer)", "Write the FAQ", "Dark mode"]),
    ("does_not_see", ["Add a card", "▶"]),
]


def model_reply(messages):
    """The stand-in model, by what it is asked: subtasks, a summary, an answer from sources, an agent's steps."""
    text = json.dumps(messages)
    if "Split this task" in text:
        return '{"subtasks": ["Pick the photo", "Write who we are", "Ask Ana to review"]}'
    if "You summarise a Kanban board" in text:
        return "One card is done, three are in progress, and the domain is late."
    if "Answer using only the sources" in text:
        return "Ana has the domain [1]."
    if "late_cards" in text:
        if "Point the DNS" in text or "2026-10-20" in text:       # the tool's rows came back
            return '{"action": "finish", "result": "Set up the domain is late; Ana has it."}'
        return '{"action": "late_cards", "args": {}}'
    return "fake answer"


@pytest.fixture
def services():
    with FakeOllama() as model, FakeForge() as forge:
        model.reply = model_reply
        yield model, forge


@pytest.fixture
def kanban(tmp_path, monkeypatch, services):
    """The application copied, migrated, its board pointed at the forge; cwd restored afterwards (run_on moves it)."""
    model, forge = services
    app = tmp_path / "kanban"
    shutil.copytree(KANBAN, app, ignore=shutil.ignore_patterns("data", ".quantum", "__pycache__"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QUANTUM_LLM_BASE_URL", model.url)
    from quantum.cli.migrations import MigrationRunner
    assert [r["status"] for r in MigrationRunner(app).up()] == ["applied"]
    db = sqlite3.connect(app / "data" / "kanban.db")
    db.execute("UPDATE boards SET issues_api = ?, webhook_url = ? WHERE id = 1", (forge.url, forge.url + "/hook"))
    db.commit()
    db.close()
    logging.disable(logging.WARNING)
    yield app
    logging.disable(logging.NOTSET)


def the_script_held(app, forge):
    """What the script left behind, the same whatever version ran it."""
    rows = sqlite3.connect(app / "data" / "kanban.db").execute
    assert rows("SELECT count(*) FROM cards WHERE labels = 'subtask'").fetchone() == (3,)
    assert rows("SELECT count(*) FROM cards WHERE source IS NOT NULL").fetchone() == (2,)
    assert rows("SELECT done_on IS NOT NULL FROM cards WHERE title = 'Write the FAQ'").fetchone() == (1,)
    assert [h["title"] for h in forge.hooks()] == ["Write the FAQ"]


def browser_script(url):
    playwright = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")
    with playwright.sync_playwright() as pw:
        try:
            chromium = pw.chromium.launch()
        except Exception as exc:   # browser not downloaded
            pytest.skip(f"Playwright's Chromium is not available: {exc}")
        try:
            page = chromium.new_page(viewport={"width": 1280, "height": 900})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url)
            run_script(Browser(page, url), SCRIPT)
            assert errors == []
        finally:
            chromium.close()


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_on_web(kanban, services, tmp_path):
    # UI-18: `quantum run <app> --on web` serves it; the script runs in a browser
    port = free_port()
    # its log goes to a file: a pipe nobody reads fills, and the server stops at its next line
    log = open(tmp_path / "server.log", "wb")
    server = subprocess.Popen([sys.executable, "-m", "quantum.cli.runner", "run", str(kanban), "--on", "web",
                               "--port", str(port)], stdout=subprocess.DEVNULL, stderr=log,
                              env={**os.environ, "QUANTUM_LLM_BASE_URL": services[0].url})
    url = f"http://127.0.0.1:{port}/"
    try:
        deadline = time.monotonic() + 60
        while True:
            assert server.poll() is None, (tmp_path / "server.log").read_text(errors="replace")
            try:
                if requests.get(url + "health", timeout=2).status_code == 200:
                    break
            except requests.ConnectionError:
                pass
            assert time.monotonic() < deadline, "the server did not answer in 60s"
            time.sleep(0.2)
        browser_script(url)
    finally:
        server.terminate()
        server.wait(10)
        log.close()
    the_script_held(kanban, services[1])


def test_on_desktop(kanban, services, monkeypatch):
    # UI-18, UI-4: `--on desktop` opens a window on the application's server; the window is a browser
    # without its chrome, so the script runs in a browser on the window's address
    from quantum.cli.platforms import run_on
    opened = []

    class Loaded:                    # what the launcher adds its title handler to
        def __iadd__(self, handler):
            return self

    def create_window(title, url, **options):
        window = types.SimpleNamespace(url=url, events=types.SimpleNamespace(loaded=Loaded()))
        opened.append(window)
        return window

    webview = types.SimpleNamespace(create_window=create_window,
                                    start=lambda **options: browser_script(opened[0].url))
    monkeypatch.setitem(sys.modules, "webview", webview)
    assert run_on(str(kanban), "desktop") == 0
    assert opened[0].url.startswith("http://127.0.0.1:")
    the_script_held(kanban, services[1])


def test_on_terminal(kanban, services, monkeypatch):
    # UI-18, UI-3: `--on terminal` draws the same pages in the terminal; the script runs through its pilot
    from quantum.cli.platforms import run_on
    from quantum.runtime.ui_console import ConsoleUI
    from tests.console_pilot import page_loaded

    def run(app):
        async def drive():
            async with app.run_test(size=(180, 200)) as pilot:
                await page_loaded(app, pilot)
                await run_console_script(app, pilot, SCRIPT)
        asyncio.run(drive())

    monkeypatch.setattr(ConsoleUI, "run", run)
    assert run_on(str(kanban), "terminal") == 0
    the_script_held(kanban, services[1])


def test_on_tui_says_it_is_not_built_yet(kanban, capsys):
    # UI-18: the TUI drawn by Godot is PLAN_PLATFORMS.md's Phase 3; until then it says so
    from quantum.cli.platforms import run_on
    assert run_on(str(kanban), "tui") == 2
    assert "Phase 3" in capsys.readouterr().err


def test_what_is_not_an_application(tmp_path, capsys):
    # UI-18
    from quantum.cli.platforms import run_on
    assert run_on(str(tmp_path), "web") == 1
    assert "is not an application" in capsys.readouterr().err


def test_the_cli(kanban, monkeypatch):
    # UI-18: the parameter, the page and the port reach the launcher
    import quantum.cli.platforms as platforms
    from quantum.cli import runner
    calls = []
    monkeypatch.setattr(platforms, "run_on", lambda *a: calls.append(a) or 0)
    monkeypatch.setattr(sys, "argv", ["quantum", "run", str(kanban), "--on", "terminal", "--page", "/board/1"])
    with pytest.raises(SystemExit) as exit_:
        runner.main()
    assert exit_.value.code == 0 and calls == [(str(kanban), "terminal", "/board/1", None)]
