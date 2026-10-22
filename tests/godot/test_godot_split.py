"""Split screen in Godot (PLAN_GAMES_3.md, Phase 5): qg:camera player=, one view per player.

One small game for two on a field wider than the screen: each walker has a camera of its own. On one machine
the screen splits in two, each half following its walker; a flag that stays in one player's half is on the
screen, and leaves it only when it is in neither. Over the network each machine shows its own player's view,
the whole screen, and the game is the same on both.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession
from quantum.runtime.godot_replay import replay, replay_peers, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

FIELD = '''<q:application id="field" type="game">
  <qg:spritesheet name="c" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:input action="right" keys="D" player="1" />
  <qg:input action="right" keys="Right" player="2" />
  <qg:input action="left" keys="Left" player="2" />
  <qg:multiplayer players="2" start="field" />
  <qg:prefab name="Flag" tag="flag" sheet="c" frame="4" hitbox="12x12" />
  <qg:scene name="field" width="320" height="180" seed="1">
    <q:set name="gone" value="0" type="number" />
    <qg:character id="p1" controller="topdown" player="1" sheet="c" x="80" y="90" hitbox="14x14" speed="120" />
    <qg:character id="p2" controller="topdown" player="2" sheet="c" x="1200" y="90" hitbox="14x14" speed="120" />
    <qg:instance prefab="Flag" name="flag" x="1200" y="40" />
    <qg:camera player="1" follow="p1" bounds="none" />
    <qg:camera player="2" follow="p2" bounds="none" />
    <qg:on-screen-exit of="flag"><q:set name="gone" value="{gone + 1}" /></qg:on-screen-exit>
  </qg:scene>
</q:application>
'''


@pytest.fixture(scope='module')
def field(tmp_path_factory, godot):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    folder = tmp_path_factory.mktemp('field')
    src = folder / 'field.q'
    src.write_text(FIELD, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(folder / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def cameras(obs):
    return {v['player']: v for v in obs['screen'] if v['kind'] == 'camera'}


def test_on_one_machine_each_half_follows_its_player(field, godot):
    with PlaySession(field, binary=godot) as game:
        seen = game.act(ticks=2)
        views = cameras(seen)
        assert sorted(views) == [1, 2]
        assert views[1]['x'] == 80 and views[2]['x'] == 1200         # each on its own walker
        moved = cameras(game.act(hold=['right'], player=2, ticks=60))
        assert moved[2]['x'] > 1300 and moved[1]['x'] == 80


def test_a_thing_in_either_half_is_on_the_screen(field, godot):
    # the flag is in player 2's half from the start; it leaves the screen only once player 2 walks away
    stay = replay(field, 60, tape=tape_from_holds([('right', 1, 60)]))['field']
    assert stay['gone'] == 0
    away = replay(field, 200, tape=tape_from_holds([('p2_right', 1, 200)]))['field']
    assert away['gone'] == 1


def test_over_the_network_each_machine_shows_its_own_and_plays_the_same(field, godot):
    tapes = [tape_from_holds([('right', 1, 100)]), tape_from_holds([('right', 1, 150)])]
    states = replay_peers(field, 220, tapes, binary=godot)
    assert states[0] == states[1]
    assert states[0]['field']['nodes']['p2']['x'] > 1400 and states[0]['field']['gone'] == 1
