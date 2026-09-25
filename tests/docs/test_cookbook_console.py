"""Cookbook recipes in the console (UI-3): the same app, drawn by `quantum console`.

`quantum test` checks a recipe in the browser's HTML. Here the recipe's app is
served as it is and opened in the console renderer (quantum/runtime/ui_console.py),
which asks for the view tree and posts the same actions a browser posts.
docs/cookbook/screens/browser-and-console.md and responsive-layout.md point here.
"""

import asyncio
import logging
import re
import shutil
import threading
from pathlib import Path

import pytest

from tests.console_pilot import page_loaded, press

SCREENS = Path(__file__).resolve().parents[2] / 'examples' / 'cookbook' / 'screens'


def serve(recipe, tmp_path, monkeypatch):
    project = tmp_path / f'{recipe}-{len(list(tmp_path.iterdir()))}'
    shutil.copytree(SCREENS / recipe, project, ignore=shutil.ignore_patterns('data', 'output', '__pycache__'))
    monkeypatch.chdir(project)
    if (project / 'migrations').is_dir():
        from quantum.cli.migrations import MigrationRunner
        MigrationRunner(project).up()
    from werkzeug.serving import make_server
    from quantum.runtime.web_server import QuantumWebServer
    app = QuantumWebServer(str(project / 'quantum.config.yaml')).app
    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_port}/'


@pytest.fixture
def console(tmp_path, monkeypatch):
    servers = []
    logging.disable(logging.WARNING)

    def run(recipe, width, script):
        from quantum.runtime.ui_console import ConsoleUI
        server, url = serve(recipe, tmp_path, monkeypatch)
        servers.append(server)

        async def main():
            app = ConsoleUI(url)
            async with app.run_test(size=(width, 50)) as pilot:
                await page_loaded(app, pilot)
                await script(app, pilot)

        asyncio.run(main())

    yield run
    for server in servers:
        server.shutdown()
    logging.disable(logging.NOTSET)


def screen_text(app) -> str:
    from textual.widgets import Button, Static
    parts = [str(w.render()) for w in app.query(Static)]
    parts += [str(b.label) for b in app.query(Button)]
    return re.sub(r'\s+', ' ', ' | '.join(parts))


def visit_texts(recipe):
    """The text= a recipe's tests expect after a plain visit of `/`, in the browser."""
    texts = []
    for test in (SCREENS / recipe / 'tests').glob('*.test.q'):
        for block in re.findall(r'<q:test [^>]*page="/">(.*?)</q:test>', test.read_text(encoding='utf-8'), re.S):
            if '<test:submit' not in block:
                texts += re.findall(r'<test:expect text="([^"]+)"', block)
    return texts


def test_what_the_browser_shows_the_console_shows(console):
    # UI-3, UI-7: the texts the recipe's quantum test expects in the HTML
    expected = visit_texts('browser-and-console')
    assert expected

    async def script(app, pilot):
        shown = screen_text(app)
        for text in expected:
            assert text in shown, f'{text!r} is not on the console screen: {shown}'
        assert app.title == 'Guest list'
    console('browser-and-console', 120, script)


def test_the_form_posts_the_same_action_from_the_console(console):
    # UI-3: the form sends the field; the rule, the flash and the session are the web's
    from textual.widgets import Button, Input

    async def script(app, pilot):
        sign = lambda: [b for b in app.query(Button) if str(b.label) == 'Sign'][0]
        app.query_one(Input).value = 'A'
        await press(app, pilot, sign())
        assert 'Must be at least 2 characters' in screen_text(app)
        app.query_one(Input).value = 'Ana'
        await press(app, pilot, sign())
        shown = screen_text(app)
        assert 'Welcome, Ana!' in shown and '1 signed so far.' in shown and 'Ana' in shown
    console('browser-and-console', 120, script)


def test_the_responsive_layout_stacks_in_a_narrow_terminal(console):
    # UI-2 in the console: stack-below="md" stacks below 96 columns
    from textual.containers import Horizontal, Vertical

    async def narrow(app, pilot):
        assert isinstance(app.query_one('#main'), Vertical)
    console('responsive-layout', 80, narrow)

    async def wide(app, pilot):
        assert isinstance(app.query_one('#main'), Horizontal)
        assert app.query_one('#side').size.width == 220 // 8      # width="220" in columns
    console('responsive-layout', 140, wide)
