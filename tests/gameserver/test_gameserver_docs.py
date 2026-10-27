"""Every ```xml block of docs/targets/gameserver.md is a world that is read against the schema and runs.

The page is generated from the schema (scripts/generate-gameserver-reference.py) and shows whole worlds; each one is
written out here, next to the map of the tests, read, and played a tick with a player in it, so the page cannot show
what the server refuses. (tests/docs/docs_blocks.py lists the page under RUN_BY_TEST.)
"""

import re
import shutil
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.gameserver import World, read_world

REPO = Path(__file__).resolve().parents[2]
PAGE = REPO / 'docs' / 'targets' / 'gameserver.md'
MAPS = Path(__file__).resolve().parent / 'worlds' / 'yard'

BLOCKS = re.findall(r'```xml\n(.*?)```', PAGE.read_text(encoding='utf-8'), re.S)


def test_the_page_shows_worlds():
    assert BLOCKS and all('type="gameserver"' in block for block in BLOCKS)


@pytest.mark.parametrize('block', BLOCKS, ids=[f'block-{i + 1}' for i in range(len(BLOCKS))])
def test_every_block_of_the_page_is_a_world_that_runs(block, tmp_path):
    for tmx in MAPS.glob('*.tmx'):
        shutil.copy(tmx, tmp_path / tmx.name)
    source = tmp_path / 'world.server.q'
    source.write_text(block, encoding='utf-8')
    world = World(read_world(QuantumParser(use_cache=False).parse_file(str(source)), str(source)))
    out = world.step([('join', 'ana')])
    assert out.joined == {'ana': world.players['ana']} and not world.errors
