"""The wheel carries the files the runtime reads from its own folders (pyproject.toml's package-data).

`pip install quantum-framework` gets only what package-data names besides the Python files: a file the
runtime reads and the wheel leaves out works in a checkout and fails for everyone who installed it. The
TUI's icon (Phase 6b) was such a file: a phone's export needs it.
"""

import fnmatch
import tomllib
from pathlib import Path

from quantum.runtime.ui_tui import PROJECT_SUFFIXES, TUI_DIR

REPO = Path(__file__).resolve().parents[2]


def package_data() -> list:
    config = tomllib.loads((REPO / 'pyproject.toml').read_text(encoding='utf-8'))
    return config['tool']['setuptools']['package-data']['quantum']


def carried(path: Path) -> bool:
    relative = path.relative_to(REPO / 'quantum').as_posix()
    return any(fnmatch.fnmatch(relative, pattern) for pattern in package_data())


def test_the_wheel_carries_every_file_of_the_tuis_project():
    project = [p for p in TUI_DIR.iterdir() if p.is_file() and p.suffix in PROJECT_SUFFIXES]
    assert {p.name for p in project} >= {'tui.gd', 'project.godot', 'icon.png'}
    assert [p.name for p in project if not carried(p)] == []


def test_the_wheel_carries_the_godot_replay_harness_and_addon():
    runtime = REPO / 'quantum' / 'runtime'
    files = [*runtime.glob('*.gd'), *(runtime / 'godot' / 'addons' / 'quantum').glob('*.gd')]
    assert files
    assert [p.name for p in files if not carried(p)] == []
