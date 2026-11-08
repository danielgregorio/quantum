"""A package made on another system runs on this one (SPEC.md UI-22): CI's package job makes the Kanban's Windows and
macOS packages on Linux, and a Windows and a macOS runner unpack them and run the start of the Kanban's script in
their program — the TUI starts the server with the package's own Python, signs in, opens a board, adds a card and
moves it. QUANTUM_PACKAGE_PROGRAM is the program to run (kanban.exe, Kanban.app/Contents/MacOS/Kanban); without
it, this is skipped.
"""

import os
import sys

import pytest

from tests.apps.ui_drivers import Tui, run_script

PROGRAM = os.environ.get('QUANTUM_PACKAGE_PROGRAM')
pytestmark = pytest.mark.skipif(not PROGRAM, reason='QUANTUM_PACKAGE_PROGRAM names a package\'s program to run')

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
