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
