"""Siege (projects/siege/siege.q), replayed in Godot.

From the title into the keep: the first wave comes from the edges; a shot let go at once is an
arrow, one held for most of a second a bolt; the tower zaps the raiders near it; left alone, the
raiders reach the tower and the keep falls, its score among the best. Over the network the second
player is the knight, who turns the horse and spurs it on.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import cursor_at, replay, replay_peers, tape_from_holds

SIEGE = Path(__file__).resolve().parents[2] / 'projects' / 'siege' / 'siege.q'
START = [('select', 2, 4)]          # Play alone, the title's first button


@pytest.fixture(scope='module')
def siege(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    out = tmp_path_factory.mktemp('siege') / 'godot'
    compile_game(QuantumParser(use_cache=False).parse_file(str(SIEGE)), str(out), source_dir=str(SIEGE.parent))
    assert check_project(out, binary=godot) == []
    return out


def run(project, ticks, holds=(), pointer=None, **kw):
    tape = tape_from_holds(START + list(holds))
    if pointer is not None:
        cursor_at(tape, 5, *pointer)
    state = replay(project, ticks, tape=tape, **kw)
    scene = next(k for k in state if not k.startswith('_'))
    return scene, state[scene]


def test_the_first_wave_comes_from_the_edges(siege, godot):
    scene, keep = run(siege, 130, binary=godot)            # two seconds after the horn, as they come
    assert scene == 'keep' and keep['game']['wave'] == 1.0
    assert keep['things'] == {'raider': 5, 'tower': 1}
    for _, x, y, *_ in (w for w in keep['where'] if w[0] == 'raider'):
        assert x < 40 or x > 280 or y < 40 or y > 200        # not inside the keep


def test_a_shot_let_go_at_once_is_an_arrow_and_a_held_one_a_bolt(siege, godot):
    _, quick = run(siege, 60, [('fire', 50, 52)], pointer=(300, 120), binary=godot)
    assert quick['things'].get('arrow') == 1 and 'bolt' not in quick['things']
    _, held = run(siege, 110, [('fire', 50, 100)], pointer=(300, 120), binary=godot)
    assert held['things'].get('bolt') == 1 and 'arrow' not in held['things']


def test_left_alone_the_keep_falls_and_its_score_is_kept(siege, godot, tmp_path):
    scene, fallen = run(siege, 1400, binary=godot, persist_dir=tmp_path)
    assert scene == 'fallen'
    game = fallen['game']
    assert game['hearts'] == 0.0 and game['score'] > 0         # the tower zapped a few before
    assert game['best'] == [game['score']]


def test_the_same_tape_gives_the_same_siege(siege, godot):
    holds = [('fire', 50, 52), ('fire', 120, 170), ('left', 60, 90), ('up', 90, 130)]
    assert run(siege, 400, holds, pointer=(60, 40), binary=godot) == \
        run(siege, 400, holds, pointer=(60, 40), binary=godot)


def test_two_defend_it_the_second_on_a_horse(siege, godot):
    knight = tape_from_holds([('up', 0, 80), ('right', 30, 50)])
    peers = replay_peers(siege, 180, [None, knight], binary=godot)
    assert peers[0] == peers[1]
    keep = peers[0]['keep']
    assert set(keep['nodes']) >= {'p1', 'p2'}
    p2 = keep['nodes']['p2']
    assert p2['x'] > 210 and p2['y'] > 125                     # spurred right, then turned down
