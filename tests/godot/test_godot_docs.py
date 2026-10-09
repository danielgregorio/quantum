"""Every ```xml block of docs/targets/games.md is a game that compiles and that Godot opens.

The page is generated from the schema and the three games
(scripts/generate-games-reference.py); the shape-of-a-game block at its top
is written by hand there. This is the guard tests/docs/docs_blocks.py names
for the page (RUN_BY_TEST).
"""

import re
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project

REPO = Path(__file__).resolve().parents[2]
PAGE = REPO / 'docs' / 'targets' / 'games.md'


def blocks():
    text = PAGE.read_text(encoding='utf-8')
    return [(text.count('\n', 0, m.start()) + 1, m.group(1))
            for m in re.finditer(r'^```xml\n(.*?)\n```', text, re.M | re.S)]


@pytest.mark.parametrize('line,source', blocks(), ids=[f'line-{line}' for line, _ in blocks()])
def test_the_block_is_a_game_godot_opens(godot, tmp_path, line, source):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path / 'game.q'
    src.write_text(source, encoding='utf-8')
    app = QuantumParser(use_cache=False).parse_file(str(src))
    # the games name assets/ and levels/ next to their own .q: compile from the project they come from
    source_dir = REPO / 'projects' / app.app_id
    if not source_dir.is_dir():
        source_dir = REPO
    out = compile_game(app, str(tmp_path / 'godot'), source_dir=str(source_dir))
    assert check_project(Path(out), binary=godot) == []
