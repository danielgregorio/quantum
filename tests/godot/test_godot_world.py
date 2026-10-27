"""A world's game in Godot (PLAN_GAME_SERVER.md, Phase 2): two clients and a test world, in step.

The meadow's game (tests/gameserver/worlds/meadow/meadow.q) is the client of the meadow's world: two of them, ana's
and bo's, headless, come into a test world that a WorldTable steps. Each sees the other as the world's view says:
walking a tile at a time, and gone when it is six tiles away. A hero's private purse reaches its own game only. A
shout is heard by both; a step into a wall is refused, and the game says why. Under an overlay that does not freeze,
the world goes on and the keys are the overlay's.
"""

from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.godot import compile_game
from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession
from quantum.runtime.godot_world import WorldTable

MEADOW = Path(__file__).resolve().parents[1] / 'gameserver' / 'worlds' / 'meadow'


@pytest.fixture(scope='module')
def meadow(godot, tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp('meadow') / 'godot'
    app = QuantumParser(use_cache=False).parse_file(str(MEADOW / 'meadow.q'))
    project = Path(compile_game(app, str(out), source_dir=str(MEADOW)))
    assert check_project(project, binary=godot) == []
    return project


@pytest.fixture
def table(meadow, godot):
    with WorldTable(MEADOW / 'meadow.server.q', meadow, seats=['ana', 'bo'], binary=godot) as t:
        yield t


def drawn(obs: dict) -> dict:
    """What the game's mirror draws: an entity's id -> where, in pixels."""
    view = PlaySession.screen(obs, 'mirror')
    return {i['id']: (i['x'], i['y']) for i in view['items']} if view else {}


def hud(obs: dict) -> list:
    return PlaySession.screen(obs, 'hud')['items']


def test_two_games_see_each_other_walk_and_leave_the_view(table):
    seen = table.observe()
    for seat in ('ana', 'bo'):
        world = seen[seat]['world']
        assert world['status'] == 'in' and world['you'] == f'hero:{seat}'
        assert set(world['entities']) == {'hero:ana', 'hero:bo'}
        assert drawn(seen[seat]) == {'hero:ana': (56.0, 56.0), 'hero:bo': (56.0, 56.0)}   # both at (3, 3)
    for _ in range(5):                                       # ana walks east, a tile a tick of the world
        seen = table.act('ana', tap=['right'])
    assert seen['ana']['world']['me']['at'] == {'x': 8, 'y': 3}
    assert seen['bo']['world']['entities']['hero:ana']['at'] == {'x': 8, 'y': 3}
    seen = table.act()                                       # the walk to the tile is drawn whole
    assert drawn(seen['bo'])['hero:ana'] == (136.0, 56.0) and drawn(seen['ana'])['hero:ana'] == (136.0, 56.0)
    seen = table.act('ana', tap=['right'])                   # six tiles apart: out of each other's view
    assert 'hero:ana' not in seen['bo']['world']['entities'] and 'hero:ana' not in drawn(seen['bo'])
    assert 'hero:bo' not in seen['ana']['world']['entities'] and 'hero:bo' not in drawn(seen['ana'])
    seen = table.act('ana', tap=['left'])                    # and back
    assert 'hero:ana' in drawn(seen['bo']) and 'hero:bo' in drawn(seen['ana'])


def test_a_private_field_reaches_its_own_game_only(table):
    seen = table.act('ana', tap=['earn'])
    assert seen['ana']['world']['me']['purse'] == 1
    assert 'ana  1 coins' in hud(seen['ana'])
    other = seen['bo']['world']['entities']['hero:ana']
    assert 'purse' not in other and other['name'] == 'ana'
    assert all('purse' not in e for e in seen['bo']['world']['views']['around'].values() if e['id'] != 'hero:bo')


def test_an_event_is_heard_and_a_refusal_said(table):
    seen = table.act('bo', tap=['shout'])
    for seat in ('ana', 'bo'):
        assert seen[seat]['state']['game']['heard'] == 'bo: hello'
        assert 'bo: hello' in hud(seen[seat])
    table.act('ana', tap=['up'])
    table.act('ana', tap=['up'])                             # at (3, 1): the wall is next
    seen = table.act('ana', tap=['up'])
    assert seen['ana']['world']['me']['at'] == {'x': 3, 'y': 1}
    assert seen['ana']['state']['game']['note'] == 'A wall.' and seen['ana']['state']['game']['refusals'] == 1
    assert seen['bo']['state']['game']['refusals'] == 0


def test_under_an_overlay_that_does_not_freeze_the_world_goes_on(table):
    seen = table.act('ana', tap=['bag'])
    assert seen['ana']['scene'] == 'bag' and seen['ana']['under'] == 'meadow'
    sent = seen['ana']['world']['sent']
    seen = table.act('bo', tap=['right'])
    assert seen['ana']['world']['entities']['hero:bo']['at'] == {'x': 4, 'y': 3}   # heard under the bag
    seen = table.act('ana', tap=['right'])                   # the bag has the keys: no step is sent
    assert seen['ana']['world']['sent'] == sent and seen['ana']['world']['me']['at'] == {'x': 3, 'y': 3}
    table.act('ana', tap=['bag'])
    seen = table.act()
    assert seen['ana']['scene'] == 'meadow' and drawn(seen['ana'])['hero:bo'] == (72.0, 56.0)
