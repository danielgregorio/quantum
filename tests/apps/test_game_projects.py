"""The game projects build to a Godot project (Laboratory).

projects/quantum-snake, quantum-tictactoe and kenney-platformer are a .q
game each, built by `quantum run <game>.q` into a Godot 4 project next to
it (projects/<id>/godot/, ignored by git). This builds each one into a
temporary directory and checks the project is there with its scenes and
scripts.

What it does not check: that Godot accepts the project. Nothing in CI has
the binary yet, and these three games were written for the HTML backend
that is gone — their q:function bodies are JavaScript, copied into the
GDScript as they are. They are the migration backlog of PLAN_GAMES_2.md,
phase 1; until then this test only guards the pipeline from parse to
project directory.

The file name starts with test_game_, so the root conftest marks it
`laboratory`: it runs in the Laboratory CI job.
"""

from pathlib import Path

import pytest

PROJECTS = Path(__file__).resolve().parents[2] / 'projects'

GAMES = [
    ('quantum-snake', 'snake.q'),
    ('quantum-tictactoe', 'tictactoe.q'),
    ('kenney-platformer', 'kenney_platformer.q'),
]


def build(project, source, out):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.game_builder import GameBuilder
    src = PROJECTS / project / source
    app = QuantumParser().parse_file(str(src))
    return Path(GameBuilder(source_dir=str(src.parent)).build_to_file(app, str(out)))


@pytest.mark.parametrize('project,source', GAMES, ids=[g[0] for g in GAMES])
def test_the_game_builds_to_a_godot_project(project, source, tmp_path):
    out = build(project, source, tmp_path / 'godot')
    assert (out / 'project.godot').is_file()
    assert list(out.rglob('*.tscn')), 'no scene was written'
    assert list(out.rglob('*.gd')), 'no script was written'
