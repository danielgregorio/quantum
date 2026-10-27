"""A world's game in Godot (PLAN_GAME_SERVER.md, Phase 3): the den's, with latency injected.

The den's world has a step with predict="true": its game shows the step at once, long before the world's answer
crosses the 100 to 250 ms the test puts between them, and when the world refuses one (a hero who shouts stands),
the hero walks back, a few pixels a tick, never a jump. The hero and the rats carry their health over them, and
the HUD's bar is the hero's, as the world says.
"""

from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.godot import compile_game
from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession
from quantum.runtime.godot_world import WorldTable

DEN = Path(__file__).resolve().parents[1] / 'gameserver' / 'worlds' / 'den'


@pytest.fixture(scope='module')
def den(godot, tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp('den') / 'godot'
    app = QuantumParser(use_cache=False).parse_file(str(DEN / 'den.q'))
    project = Path(compile_game(app, str(out), source_dir=str(DEN)))
    assert check_project(project, binary=godot) == []
    return project


def drawn(obs: dict, eid: str = 'hero:ana'):
    view = PlaySession.screen(obs, 'mirror')
    return {i['id']: (i['x'], i['y']) for i in view['items']}.get(eid) if view else None


@pytest.mark.parametrize('latency', [100, 250])
def test_a_step_is_shown_at_once_and_a_refused_one_walks_back(den, godot, latency):
    with WorldTable(DEN / 'den.server.q', den, seats=['ana'], binary=godot, latency=latency) as table:
        game = table.games['ana']
        start = drawn(game.observe())
        assert start == (56.0, 56.0)                                       # (3, 3), at 16 pixels a tile
        game.act(tap=['right'], ticks=1)
        seen = game.act(ticks=2)
        assert drawn(seen)[0] > start[0]                                   # walking, three ticks after the key
        assert seen['world']['me']['at'] == {'x': 3, 'y': 3}               # the world has not said yes yet
        assert seen['world']['guessed'] == 1
        seen = table.act(ticks=4)['ana']
        assert seen['world']['me']['at'] == {'x': 4, 'y': 3} and seen['world']['guessed'] == 0
        assert drawn(seen) == (72.0, 56.0)                                 # where the world says: nothing moved
        table.act('ana', tap=['shout'], ticks=4)
        game.act(tap=['right'], ticks=1)
        xs = []
        for frame in range(60):
            xs.append(drawn(game.act(ticks=1))[0])
            if frame % 6 == 5:
                table._step()                                              # the world's ticks go on
        assert max(xs) > 72.0                                               # it went, as a step not refused yet
        assert xs[-1] == 72.0                                               # and came back where the world says
        assert max(abs(b - a) for a, b in zip([72.0] + xs, xs)) <= 6.0     # walking, never a jump of a tile
        last = game.observe()
        assert last['state']['game']['note'] == 'You are shouting.' and last['state']['game']['refusals'] == 1


def health(obs: dict) -> list:
    """The health bars over what is drawn: how full each is."""
    return [v['bars'][0] for v in obs['screen'] if v['kind'] == 'label' and v.get('bars')]


def test_the_rat_bites_and_the_bars_say_so(den, godot):
    with WorldTable(DEN / 'den.server.q', den, seats=['ana'], binary=godot) as table:
        seen = table.observe()['ana']
        assert health(seen) == [1.0]                                       # her own, whole; the rat is far
        assert {'bar': '_q_bar_0', 'max': 30.0, 'value': 30.0} in PlaySession.screen(seen, 'hud')['items']
        seen = table.act('ana', tap=['den'])['ana']                        # off to the square, around the wall
        for _ in range(150):
            if seen['world']['me']['hp'] < 30:
                break
            seen = table.act()['ana']
        rat = next(e for e in seen['world']['entities'].values() if e['kind'] == 'Rat')
        assert rat['state'] == 'bite' and rat['target'] == 'hero:ana' and seen['world']['me']['hp'] < 30
        seen = table.act()['ana']
        hp = seen['world']['me']['hp']
        assert sorted(health(seen)) == [round(hp / 30, 2), 1.0]            # hers bitten, the rat's whole
        assert {'bar': '_q_bar_0', 'max': 30.0, 'value': hp} in PlaySession.screen(seen, 'hud')['items']
