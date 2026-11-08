"""The TUI in the browser (SPEC.md UI-22, PLAN_PLATFORMS.md Phase 5c): `quantum package <app> --target web` exports it
into the application's static folder, the application's own server serves it (/static/tui/index.html), and it asks
that server for the pages through the browser's fetch — the browser's cookies the session, its redirects followed.

The same scripts run in it, in Chromium, through window.quantumTui (quantum/runtime/ui_tui.py, TuiInBrowser): the
parity script's three (tests/apps/test_ui_parity_script.py); a file chosen in the browser's own picker and sent, a
picture, search as you type and an editable cell (the application of tests/tui/); and the Kanban's whole script
(tests/apps/test_kanban_everywhere.py), which signs in and out, reads a stream and calls the API.

They need Godot's export templates for the web and Playwright's Chromium: skipped without them, and a failure with
QUANTUM_PACKAGE_TESTS=1 (CI's package job).
"""

import logging
import os
import shutil
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest
import requests

from tests.apps.test_kanban_everywhere import SCRIPT as KANBAN_SCRIPT, kanban, services, the_script_held  # noqa: F401
from tests.apps.test_ui_parity_script import MORE, SCRIPT, SHOWCASE, STATE
from tests.apps.ui_drivers import Tui, run_script
from tests.package.test_package_kanban import summary
from tests.tui.conftest import app_url  # noqa: F401 (the application of the TUI's own tests)

REQUIRED = bool(os.environ.get('QUANTUM_PACKAGE_TESTS'))
# WebGL without a GPU (SwiftShader), as scripts/check-games-in-browser.py runs the games
CHROMIUM_ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']


def missing(reason):
    if REQUIRED:
        pytest.fail(reason)
    pytest.skip(reason)


@pytest.fixture(scope='module')
def web_tui(tmp_path_factory):
    """The TUI exported for the browser, once: `quantum package` of the showcase, into its static folder."""
    from quantum.runtime.godot_bin import GODOT_VERSION, GodotNotFound, ensure_godot
    from quantum.runtime.godot_export import have_templates, templates_dir
    from quantum.runtime.package import build
    try:
        ensure_godot()
    except GodotNotFound as exc:
        missing(str(exc))
    cached = Path.home() / '.cache' / 'quantum' / f'godot-{GODOT_VERSION}-export-templates.tpz'   # install_templates's
    if not have_templates('Web') and not cached.is_file() and not REQUIRED:
        pytest.skip(f'no export templates for the web in {templates_dir()} (scripts/export-games.py '
                    f'--install-templates); QUANTUM_PACKAGE_TESTS=1 fetches them')
    app = tmp_path_factory.mktemp('web') / 'showcase'
    shutil.copytree(SHOWCASE, app, ignore=shutil.ignore_patterns('__pycache__', 'logs'))
    made = build(app, on='tui', target='web', progress=print)
    assert made.path == app.resolve() / 'static' / 'tui' / 'index.html'
    assert {'index.html', 'index.js', 'index.wasm', 'index.pck'} <= {f.name for f in made.folder.iterdir()}
    assert not (app / 'dist').exists()                       # no server, no Python: the application's is the one
    return made


@pytest.fixture(scope='module')
def chromium():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        missing('Playwright is not installed')
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(args=CHROMIUM_ARGS)
        except Exception as exc:   # its Chromium not downloaded
            missing(f"Playwright's Chromium is not available: {exc}")
        yield browser
        browser.close()


@contextmanager
def tui_in_browser(chromium, web_tui, project, url, cols=160, rows=63, path='/'):
    """The exported TUI in `project`'s static folder, opened in a page of `cols` x `rows` cells (10 x 19 pixels)."""
    from quantum.runtime.ui_tui import TuiInBrowser
    shutil.copytree(web_tui.folder, project / 'static' / 'tui', dirs_exist_ok=True)
    page = chromium.new_page(viewport={'width': cols * 10, 'height': (rows + 2) * 19})
    try:
        tui = TuiInBrowser(page, url, path=path)
        assert (tui.last['cols'], tui.last['rows']) == (cols, rows)
        yield tui
        # nothing went wrong in the page: what it did not find is the application's (the showcase's /logo.png)
        assert [e for e in tui.errors if not e.startswith('Failed to load resource')] == []
    finally:
        page.close()


@contextmanager
def serving(project):
    """The application in `project` served on a local port, as tests/apps/test_ui_parity_script.py's `url` is."""
    from werkzeug.serving import make_server
    from quantum.runtime.web_server import QuantumWebServer
    cwd = os.getcwd()
    os.chdir(project)
    logging.disable(logging.WARNING)
    server = make_server('127.0.0.1', 0, QuantumWebServer(str(project / 'quantum.config.yaml')).app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/'
    finally:
        server.shutdown()
        logging.disable(logging.NOTSET)
        os.chdir(cwd)


def test_the_parity_scripts_in_the_tui_in_the_browser(web_tui, chromium, tmp_path):
    # UI-7, UI-20, UI-22: the application's server serves the TUI, and the same three scripts pass in it
    project = tmp_path / 'showcase'
    shutil.copytree(SHOWCASE, project, ignore=shutil.ignore_patterns('__pycache__', 'logs'))
    with serving(project) as url:
        with tui_in_browser(chromium, web_tui, project, url) as tui:
            wasm = requests.get(url + 'static/tui/index.wasm', timeout=30)
            assert wasm.status_code == 200 and wasm.headers['Content-Type'] == 'application/wasm'
            assert tui.url == url.rstrip('/') and tui.last['path'] == '/'      # the page's origin is the server
            run_script(Tui(tui), SCRIPT)
            assert tui.observe()['unsupported'] == []
            run_script(Tui(tui), MORE)
            run_script(Tui(tui), STATE)
    summary(f'| TUI for the browser | {web_tui.size / 1e6:.1f} MB | first page in {tui.first_page:.2f} s '
            f'(Chromium, SwiftShader) | made in {web_tui.seconds:.0f} s |')


def test_a_file_a_picture_search_and_a_cell_in_the_browser(web_tui, chromium, app_url, tmp_path):  # noqa: F811
    # UI-12, UI-13, UI-14: what the parity script does not reach, as tests/tui/test_tui.py does it natively
    url, project = app_url
    with tui_in_browser(chromium, web_tui, project, url, cols=100, rows=30) as tui:
        image, = tui.observe()['images']
        assert image['alt'] == 'Brick' and image['loaded'] is True      # its bytes through fetch, drawn
        field = tui.item('input', bind='q')
        tui.click(field['x'], field['y'])
        seen = tui.type('an')
        assert seen['path'] == '/?q=an' and 'Banana' in tui.text() and 'Apple' not in tui.text()
        assert tui.item('input', bind='q')['focus']
        tui.visit('/')
        cell = tui.item('input', bind='value', value='Apple')
        tui.click(cell['x'], cell['y'])
        tui.key('ctrl+u')
        tui.type('Apricot')
        tui.key('enter')
        rows = sqlite3.connect(project / 'fruits.db').execute('SELECT name FROM fruits ORDER BY id').fetchall()
        assert rows == [('Apricot',), ('Banana',), ('Cherry',)]
        # the browser's own picker; the form sends the file it read
        note = tmp_path / 'note.txt'
        note.write_text('hello', encoding='utf-8')
        tui.attach('doc', note)
        assert tui.item('file', bind='doc')['file'] == 'note.txt'
        send = tui.item('button', 'Send')
        tui.click(send['x'], send['y'])
        assert 'Got note.txt' in tui.text()
        assert (project / 'uploads' / 'note.txt').read_text(encoding='utf-8') == 'hello'


def test_the_kanbans_script_in_the_tui_in_the_browser(web_tui, chromium, kanban, services):  # noqa: F811
    # UI-18, UI-22: signed in and out by the browser's cookies, a stream read as it is written, the API beside it;
    # opened on the page its address names (/static/tui/index.html?page=/login)
    with serving(kanban) as url:
        with tui_in_browser(chromium, web_tui, kanban, url, cols=180, rows=60, path='/login') as tui:
            assert tui.last['path'] == '/login' and 'Sign in' in tui.text()
            run_script(Tui(tui), KANBAN_SCRIPT)
    the_script_held(kanban, services[1])
