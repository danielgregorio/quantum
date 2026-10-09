"""Godot for the tests in this directory.

The binary is the pinned one (quantum/runtime/godot_bin.py). Without it the
tests skip, so a developer who never builds a game is not blocked; in CI the
Laboratory job installs it and sets QUANTUM_GODOT_REQUIRED=1, so a missing
binary there is a failure, not a silent skip.

The file names start with test_godot_, so the root conftest marks them
`laboratory`.
"""

import os
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import GodotNotFound, ensure_godot

FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.fixture(scope='session')
def godot() -> Path:
    try:
        return ensure_godot()
    except GodotNotFound as e:
        if os.environ.get('QUANTUM_GODOT_REQUIRED'):
            pytest.fail(str(e))
        pytest.skip(str(e))


@pytest.fixture
def mover_project(tmp_path) -> Path:
    """A copy of the smallest game: tests may break it on purpose."""
    import shutil
    dst = tmp_path / 'mover'
    shutil.copytree(FIXTURES / 'mover', dst)
    return dst
