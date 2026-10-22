"""Marches — a skirmish on a map of hexes, turn by turn — played in Godot.

projects/marches/marches.q is compiled and played through the play protocol, as an agent plays it. Its map is
14 hexes by 10, 28 pixels wide with their points up, rows 24 apart and every other row 14 on; the riders stand at
the keep's side of the river, the raiders east of it. A ride is the cheapest way, four moves a turn (a forest or a
ford 2, the hills and the marsh 3); the raiders ride at the nearest rider, three moves each, and strike it if they
end next to it. The language it asked for is tested in tests/godot/test_godot_hexes.py.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession

MARCHES = Path(__file__).resolve().parents[2] / 'projects' / 'marches' / 'marches.q'
BIRCH = (112, 88)        # a rider: column 3 of row 3
EAST = (168, 88)         # two hexes on, past the hills: 3 moves


@pytest.fixture(scope='module')
def marches(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    out = tmp_path_factory.mktemp('marches') / 'godot'
    compile_game(QuantumParser(use_cache=False).parse_file(str(MARCHES)), str(out), source_dir=str(MARCHES.parent))
    assert check_project(out, binary=godot) == []
    return out


def _field(game):
    game.until("scene == 'field'", tap=['select'], max_ticks=60)
    return game.act(ticks=30)


def _click(game, at, ticks=2):
    game.act(cursor=at, ticks=1)                                  # the pointer there first, then the click
    return game.act(cursor=at, tap=['select', 'click'], ticks=ticks)


def _hud(seen):
    return PlaySession.screen(seen, 'hud')['items']


def _end_turns(game, n):
    for _ in range(n):
        seen = game.act(tap=['end-turn'], ticks=100)
    return seen


def test_a_rider_rides_by_the_cheapest_way_four_moves_a_turn(marches, godot):
    with PlaySession(marches, binary=godot) as game:
        assert _hud(_field(game))[0] == 'Click a rider.'
        assert _hud(_click(game, BIRCH))[0] == 'Where to? Four moves.'
        assert _hud(game.act(cursor=EAST, ticks=2))[1] == 'Grass: 3 moves'            # cost(chosen, aim)
        assert _hud(game.act(cursor=(196, 88), ticks=2))[1] == 'Ford: 5 moves'       # too far this turn
        rode = _click(game, EAST, ticks=40)
        assert [(e['who'], e['cells']) for e in rode['events'] if e['kind'] == 'travel'] == [('birch', 3)]
        assert (rode['state']['named']['birch']['x'], rode['state']['named']['birch']['y']) == (168.0, 88.0)
        assert _hud(rode)[0] == 'Choose another rider, or end the turn (E).'
        again = _click(game, (196, 112))                                               # once a turn
        assert _hud(again)[0] == 'Too far, or no way there.' and not [e for e in again['events'] if e['kind'] == 'travel']


def test_the_raiders_ride_and_the_turn_comes_back(marches, godot):
    with PlaySession(marches, binary=godot) as game:
        _field(game)
        ended = game.act(tap=['end-turn'], ticks=2)
        assert _hud(ended)[0] == 'The raiders ride.'
        assert sorted((e['who'], e['cells']) for e in ended['events'] if e['kind'] == 'travel') == [
            ('raider-1', 2), ('raider-2', 2), ('raider-3', 1), ('raider-4', 3)]
        assert _hud(game.act(cursor=BIRCH, tap=['select', 'click'], ticks=2))[0] == 'Wait for the raiders.'
        back = game.act(ticks=100)
        assert _hud(back)[0] == 'Your turn: click a rider.'
        named = back['state']['named']
        assert [(named[r]['x'], named[r]['y']) for r in ('raider-1', 'raider-2', 'raider-3', 'raider-4')] == [
            (322.0, 64.0), (308.0, 88.0), (308.0, 184.0), (280.0, 232.0)]


def test_a_rider_strikes_a_raider_next_to_it_once(marches, godot):
    with PlaySession(marches, binary=godot) as game:
        _field(game)
        seen = _end_turns(game, 5)                    # the second raider has come over the ford, beside birch
        assert (seen['state']['named']['raider-2']['x'], seen['state']['named']['raider-2']['y']) == (126.0, 112.0)
        _click(game, BIRCH)
        blow = _click(game, (126, 112))
        assert _hud(blow)[0] == 'A blow!'
        assert [(e['what'], e['health']) for e in blow['events'] if e['kind'] == 'damage'] == [('raider-2', 1)]
        assert _hud(_click(game, BIRCH))[0] == 'That rider is spent.'


def test_left_alone_the_march_is_lost(marches, godot):
    with PlaySession(marches, binary=godot) as game:
        _field(game)
        for turn in range(12):
            seen = game.act(tap=['end-turn'], ticks=100)
            if seen['scene'] != 'field':
                break
        assert seen['scene'] == 'lost' and turn >= 5


def test_the_march_in_portuguese(marches, godot):
    with PlaySession(marches, binary=godot, lang='pt') as game:
        assert _hud(_field(game))[0] == 'Clique num cavaleiro.'
        _click(game, BIRCH)
        assert _hud(game.act(cursor=EAST, ticks=2)) == ['Para onde? Quatro movimentos.', 'Campo: 3 movimentos']
        assert _hud(game.act(cursor=(140, 64), ticks=2))[1] == 'Pântano: 6 movimentos'
