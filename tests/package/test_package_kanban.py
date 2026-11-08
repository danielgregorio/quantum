"""The Kanban, packaged (SPEC.md UI-22, PLAN_PLATFORMS.md Phase 5): one file whose program is the TUI, which starts
the server beside it — a Python of its own, Quantum, the libraries, the application. CI's package job builds it,
unpacks it and runs the Kanban's whole script in its program (tests/apps/test_kanban_everywhere.py's SCRIPT, through
the TUI's play protocol), and makes the Windows and macOS packages, whose layout it checks; a Windows and a macOS
runner then run those (tests/package/test_package_runs_here.py). The package's size and
the time to its first page are measured and written to the job's summary.

They need the network (Python's build, pip's libraries) and Godot's export templates: QUANTUM_PACKAGE_TESTS=1 runs
them (CI's package job); otherwise they are skipped.
"""

import json
import os
import sqlite3
import tarfile
import zipfile

import pytest

from tests.apps.test_kanban_everywhere import SCRIPT, kanban, services, the_script_held  # noqa: F401 (fixtures)
from tests.apps.ui_drivers import Tui, run_script

pytestmark = pytest.mark.skipif(not os.environ.get('QUANTUM_PACKAGE_TESTS'),
                                reason='QUANTUM_PACKAGE_TESTS=1 builds packages (network, Godot templates)')

# The board's answer from its own cards needs chromadb, which a package does not carry (the application did not
# ask for it): the script without it.
RAG_STEPS = [("fill", "question", "Who has the domain?"), ("click", "Ask"),
             ("sees", ["Ana has the domain [1].", "Set up the domain (Doing, Ana"])]
PACKAGE_SCRIPT = [step for step in SCRIPT if step not in RAG_STEPS]

def summary(line):
    path = os.environ.get('GITHUB_STEP_SUMMARY')
    if path:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')


def test_the_kanban_packaged_for_linux_runs_its_script(kanban, services, tmp_path):  # noqa: F811
    from quantum.runtime.package import build
    from quantum.runtime.ui_tui import TuiSession
    made = build(kanban, on='tui', target='linux', out=tmp_path / 'dist', with_data=True, progress=print)
    assert made.path.name == 'kanban-linux.tar.gz'
    # what is handed over: the archive, unpacked somewhere else
    with tarfile.open(made.path) as tar:
        tar.extractall(tmp_path / 'unpacked', filter='tar')
    program = tmp_path / 'unpacked' / 'kanban' / 'kanban'
    assert os.access(program, os.X_OK)
    env = {**os.environ, 'XDG_DATA_HOME': str(tmp_path / 'xdg')}
    with TuiSession(program=program, cols=180, rows=60, env=env, timeout=90) as tui:
        first_page = tui.first_page
        assert tui.url.startswith('http://127.0.0.1:')
        run_script(Tui(tui), PACKAGE_SCRIPT)
    # what the script did is in the user's folder, not in the package
    the_script_held(tmp_path / 'xdg' / 'quantum' / 'kanban', services[1])
    carried = sqlite3.connect(tmp_path / 'unpacked' / 'kanban' / 'server' / 'app' / 'data' / 'kanban.db')
    assert carried.execute("SELECT count(*) FROM cards WHERE title = 'Write the FAQ'").fetchone() == (0,)
    summary(f'| Kanban, linux | {made.size / 1e6:.1f} MB | first page in {first_page:.2f} s | '
            f'made in {made.seconds:.0f} s |')
    assert made.size < 100e6 and first_page < 20


@pytest.mark.parametrize('target', ['windows', 'macos'])
def test_the_kanban_packaged_for_another_system(kanban, services, tmp_path, target):  # noqa: F811
    from quantum.runtime.package import build
    # QUANTUM_PACKAGE_OUT keeps them: CI's package job hands them to a Windows and a macOS runner, which run them
    # (tests/package/test_package_runs_here.py)
    out = os.environ.get('QUANTUM_PACKAGE_OUT') or tmp_path / 'dist'
    made = build(kanban, on='tui', target=target, out=out, progress=print)
    assert made.path.name == f'kanban-{target}.zip'
    with zipfile.ZipFile(made.path) as z:
        names = set(z.namelist())
    if target == 'windows':
        root = 'kanban/'
        assert {root + 'kanban.exe', root + 'server/python/python.exe', root + 'server/package.json'} <= names
        site = root + 'server/python/Lib/site-packages/'
        assert any(n.startswith(site + 'bcrypt/') and n.endswith('.pyd') for n in names)   # Windows's build
    else:
        root = 'Kanban.app/Contents/'
        assert {root + 'MacOS/Kanban', root + 'Resources/server/package.json'} <= names
        site = root + 'Resources/server/python/lib/python3.12/site-packages/'
        assert any(n.startswith(site + 'bcrypt/') and n.endswith('.so') for n in names)
    assert any(n.endswith('site-packages/quantum/runtime/packaged_server.py') for n in names)
    assert not any(n.endswith('data/kanban.db') for n in names)          # its data stays here
    config = json.loads((made.folder / ('Contents/Resources/server' if target == 'macos' else 'server')
                         / 'package.json').read_text())
    assert config['python'] == ('python/python.exe' if target == 'windows' else 'python/bin/python3')
    summary(f'| Kanban, {target} | {made.size / 1e6:.1f} MB | (built, not run here) | made in {made.seconds:.0f} s |')


@pytest.mark.parametrize('target', ['windows', 'macos'])
def test_the_kanban_packaged_with_a_window(kanban, services, tmp_path, target):  # noqa: F811
    # --on desktop: its program a window of its own on the system's web view (WebView2, WKWebView), run by the
    # package's Python; a Windows and a macOS runner run them (test_package_runs_here.py)
    from quantum.runtime.package import build
    out = os.environ.get('QUANTUM_PACKAGE_OUT') or tmp_path / 'dist'
    made = build(kanban, on='desktop', target=target, out=out, progress=print)
    assert made.path.name == f'kanban-{target}-desktop.zip'
    with zipfile.ZipFile(made.path) as z:
        names = set(z.namelist())
        if target == 'windows':
            program = z.read('kanban/Kanban.exe')
            assert b'#!<launcher_dir>\\server\\python\\pythonw.exe' in program
            assert {'kanban/server/python/pythonw.exe', 'kanban/server/package.json'} <= names
            assert any(n.startswith('kanban/server/python/Lib/site-packages/pythonnet/') for n in names)
        else:
            assert {'Kanban.app/Contents/Info.plist', 'Kanban.app/Contents/MacOS/Kanban',
                    'Kanban.app/Contents/Resources/server/package.json'} <= names
            assert b'quantum.runtime.packaged_desktop' in z.read('Kanban.app/Contents/MacOS/Kanban')
            assert any('site-packages/WebKit/' in n for n in names)
    summary(f'| Kanban, {target}, a window | {made.size / 1e6:.1f} MB | (built, not run here) | '
            f'made in {made.seconds:.0f} s |')


def hosted(kanban, model_url, tmp_path, port=None):
    """The Kanban served as a hosted application is (`quantum run --on web`), on a port; returns (process, url)."""
    import subprocess
    import sys
    import time

    import requests

    from tests.apps.test_kanban_everywhere import free_port
    port = port or free_port()
    log = open(tmp_path / 'hosted.log', 'wb')
    process = subprocess.Popen([sys.executable, '-m', 'quantum.cli.runner', 'run', str(kanban), '--on', 'web',
                                '--port', str(port)], stdout=subprocess.DEVNULL, stderr=log,
                               env={**os.environ, 'QUANTUM_LLM_BASE_URL': model_url})
    url = f'http://127.0.0.1:{port}'
    deadline = time.monotonic() + 60
    while True:
        assert process.poll() is None, (tmp_path / 'hosted.log').read_text(errors='replace')
        try:
            if requests.get(url + '/health', timeout=2).status_code == 200:
                return process, url
        except requests.ConnectionError:
            pass
        assert time.monotonic() < deadline, 'the hosted Kanban did not answer in 60 s'
        time.sleep(0.2)


def test_the_kanban_client_runs_its_script_against_the_hosted_application(kanban, services, tmp_path):  # noqa: F811
    # Phase 6, --server: the package is the TUI alone, which asks the hosted application; the whole script
    from quantum.runtime.package import build
    from quantum.runtime.ui_tui import TuiSession
    process, url = hosted(kanban, services[0].url, tmp_path)
    try:
        made = build(kanban, on='tui', target='linux', out=tmp_path / 'dist', server=url, progress=print)
        assert made.path.name == 'kanban-linux-client.tar.gz' and made.libraries == {}
        with tarfile.open(made.path) as tar:
            names = tar.getnames()
            tar.extractall(tmp_path / 'unpacked', filter='tar')
        assert names == ['kanban', 'kanban/kanban']                     # the program, nothing beside it
        with TuiSession(program=tmp_path / 'unpacked' / 'kanban' / 'kanban', cols=180, rows=60, timeout=90) as tui:
            first_page = tui.first_page
            assert tui.url == url
            run_script(Tui(tui), SCRIPT)
    finally:
        process.terminate()
        process.wait(10)
    the_script_held(kanban, services[1])                               # in the hosted application's database
    summary(f'| Kanban, linux, a client of a hosted Kanban | {made.size / 1e6:.1f} MB | first page in '
            f'{first_page:.2f} s | made in {made.seconds:.0f} s |')


@pytest.mark.parametrize('on', ['tui', 'desktop'])
@pytest.mark.parametrize('target', ['windows', 'macos'])
def test_the_kanban_clients_for_other_systems(kanban, services, tmp_path, target, on):  # noqa: F811
    # the clients a Windows and a macOS runner run against a Kanban they host (test_package_runs_here.py)
    from quantum.runtime.package import build
    out = os.environ.get('QUANTUM_PACKAGE_OUT') or tmp_path / 'dist'
    server = os.environ.get('QUANTUM_PACKAGE_CLIENT_SERVER', 'http://127.0.0.1:8095')
    made = build(kanban, on=on, target=target, out=out, server=server, progress=print)
    kind = f'{target}-desktop-client' if on == 'desktop' else f'{target}-client'
    assert made.path.name == f'kanban-{kind}.zip'
    with zipfile.ZipFile(made.path) as z:
        names = set(z.namelist())
    assert not any('/app/' in n for n in names)                         # no application beside a client
    if on == 'tui':
        assert not any('/server/' in n for n in names)
    else:
        config = next(n for n in names if n.endswith('server/package.json'))
        with zipfile.ZipFile(made.path) as z:
            assert json.loads(z.read(config))['server'] == server
    summary(f'| Kanban, {target}, {on}, a client | {made.size / 1e6:.1f} MB | (built, run on its system) | '
            f'made in {made.seconds:.0f} s |')
