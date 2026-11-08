"""A package made on another system runs on this one (SPEC.md UI-22): CI's package job makes the Kanban's Windows and
macOS packages on Linux, and a Windows and a macOS runner unpack them and run the start of the Kanban's script in
their program — the TUI starts the server with the package's own Python, signs in, opens a board, adds a card and
moves it. QUANTUM_PACKAGE_PROGRAM is the program to run (kanban.exe, Kanban.app/Contents/MacOS/Kanban); without
it, this is skipped. QUANTUM_PACKAGE_DESKTOP is a desktop package's program (Kanban.exe, Kanban.app/...): it runs
with no window (QUANTUM_PACKAGE_CHECK), says its first page and imports its window's library.
"""

import os
import sys

import pytest

from tests.apps.ui_drivers import Tui, run_script

PROGRAM = os.environ.get('QUANTUM_PACKAGE_PROGRAM')
DESKTOP = os.environ.get('QUANTUM_PACKAGE_DESKTOP')
CLIENT = os.environ.get('QUANTUM_PACKAGE_CLIENT')                    # a client's TUI (Phase 6, --server)
DESKTOP_CLIENT = os.environ.get('QUANTUM_PACKAGE_DESKTOP_CLIENT')    # a client's window
HOSTED_PORT = 8095                                                   # where the clients were made to ask

# the Kanban's script up to a card moved (tests/apps/test_kanban_everywhere.py), on the board its migrations make
SCRIPT = [
    ("visit", "/login"), ("fill", "email", "bruno@example.com"), ("fill", "password", "kanban-demo"),
    ("click", "Sign in"),
    ("sees", ["Bruno (member)", "Website launch", "6 cards"]),
    ("follow", "Open Website launch"),
    ("sees", ["To do 2", "Doing 2/3"]),
    ("fill", "title", "Write the FAQ"),
    ("click", "Add a card"),
    ("sees", ["Card added: Write the FAQ", "To do 3"]),
    ("click_in", "Write the FAQ", "▶"),
    ("sees", ["Doing 3/3"]),
]


@pytest.mark.skipif(not PROGRAM, reason="QUANTUM_PACKAGE_PROGRAM names a package's program to run")
def test_the_package_runs_on_this_system(tmp_path):
    from quantum.runtime.ui_tui import TuiSession
    # the user's folder, somewhere of the test's own
    env = {**os.environ, 'XDG_DATA_HOME': str(tmp_path), 'LOCALAPPDATA': str(tmp_path), 'HOME': str(tmp_path)}
    with TuiSession(program=PROGRAM, cols=180, rows=60, env=env, timeout=120) as tui:
        first_page = tui.first_page
        run_script(Tui(tui), SCRIPT)
    where = {'win32': tmp_path / 'Quantum' / 'kanban',
             'darwin': tmp_path / 'Library' / 'Application Support' / 'Quantum' / 'kanban'}.get(
        sys.platform, tmp_path / 'quantum' / 'kanban')
    assert (where / 'data' / 'kanban.db').is_file(), list(tmp_path.rglob('*'))[:20]
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write(f'The Kanban\'s package on {sys.platform}: the first page in {first_page:.2f} s, '
                    f'its script up to a card moved passed.\n')


@pytest.mark.skipif(not DESKTOP, reason="QUANTUM_PACKAGE_DESKTOP names a desktop package's program to run")
def test_the_desktop_package_runs_on_this_system(tmp_path):
    import json
    import subprocess
    result = tmp_path / 'check.json'
    env = {**os.environ, 'QUANTUM_PACKAGE_CHECK': str(result), 'XDG_DATA_HOME': str(tmp_path),
           'LOCALAPPDATA': str(tmp_path), 'HOME': str(tmp_path)}
    done = subprocess.run([DESKTOP], env=env, timeout=180, capture_output=True, text=True)
    assert result.is_file(), (done.returncode, done.stdout[-2000:], done.stderr[-2000:],
                              [str(p) for p in tmp_path.rglob('server.log')])
    said = json.loads(result.read_text())
    assert done.returncode == 0 and said.get('status') == 200 and said.get('title') == 'Kanban', said
    assert said['window'] == {'win32': 'webview.platforms.edgechromium', 'darwin': 'webview.platforms.cocoa'}[
        sys.platform]
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write(f"The Kanban's desktop package on {sys.platform}: the first page in {said['first_page']:.2f} s, "
                    f"its window's library ({said['window']}) imported.\n")


@pytest.fixture
def hosted_kanban(tmp_path):
    """projects/kanban served on the port the clients were made for, as a hosted application is."""
    import shutil
    import subprocess
    import time
    from pathlib import Path

    import requests
    repo = Path(__file__).resolve().parents[2]
    app = tmp_path / 'kanban'
    shutil.copytree(repo / 'projects' / 'kanban', app, ignore=shutil.ignore_patterns('data', '__pycache__', '.quantum*'))
    from quantum.cli.migrations import MigrationRunner
    assert [r['status'] for r in MigrationRunner(app).up()] == ['applied']
    log = open(tmp_path / 'hosted.log', 'wb')
    process = subprocess.Popen([sys.executable, '-m', 'quantum.cli.runner', 'run', str(app), '--on', 'web',
                                '--port', str(HOSTED_PORT)], stdout=subprocess.DEVNULL, stderr=log)
    url = f'http://127.0.0.1:{HOSTED_PORT}'
    try:
        deadline = time.monotonic() + 90
        while True:
            assert process.poll() is None, (tmp_path / 'hosted.log').read_text(errors='replace')
            try:
                if requests.get(url + '/health', timeout=2).status_code == 200:
                    break
            except requests.ConnectionError:
                pass
            assert time.monotonic() < deadline, 'the hosted Kanban did not answer'
            time.sleep(0.3)
        yield url
    finally:
        process.terminate()
        process.wait(10)


@pytest.mark.skipif(not CLIENT, reason="QUANTUM_PACKAGE_CLIENT names a client package's program to run")
def test_the_client_package_runs_on_this_system(hosted_kanban, tmp_path):
    from quantum.runtime.ui_tui import TuiSession
    with TuiSession(program=CLIENT, cols=180, rows=60, timeout=120) as tui:
        assert tui.url == hosted_kanban
        run_script(Tui(tui), SCRIPT)


@pytest.mark.skipif(not DESKTOP_CLIENT, reason="QUANTUM_PACKAGE_DESKTOP_CLIENT names a client's window program")
def test_the_desktop_client_runs_on_this_system(hosted_kanban, tmp_path):
    import json
    import subprocess
    result = tmp_path / 'check.json'
    env = {**os.environ, 'QUANTUM_PACKAGE_CHECK': str(result), 'XDG_DATA_HOME': str(tmp_path),
           'LOCALAPPDATA': str(tmp_path), 'HOME': str(tmp_path)}
    done = subprocess.run([DESKTOP_CLIENT], env=env, timeout=180, capture_output=True, text=True)
    said = json.loads(result.read_text())
    assert done.returncode == 0 and said.get('status') == 200 and said['url'].startswith(hosted_kanban), said
