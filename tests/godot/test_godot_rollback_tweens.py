"""Tweens, qg:set-tile, qg:after and qg:when under rollback, in Godot.

Two fighters on two Godots with rollback="8", their frames held back 120 and
30 ms so each guesses the other's input wrong and goes back. Each punch of the
first player tints the second, pulses its scale (a tween whose qg:on-end adds
to the count), puts a tile in the next cell of the row and puts off a count
of the scene's ticks (qg:after); a qg:when sees the second punch. The second player's
machine learns of each punch late, after it has run those ticks without it:
it goes back, and the tweens, tiles, delays and conditions of the ticks it runs
again must be what they would have been. Both end where one replay of both tapes ends.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, replay_peers, tape_from_holds

REPO = Path(__file__).resolve().parents[2]
DELAY = 2

FIGHT = f'''<q:application id="rollback-tweens" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="c" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:input action="punch" keys="J" />
  <qg:multiplayer players="2" delay="{DELAY}" rollback="8" start="fight" />
  <qg:scene name="fight" width="320" height="180">
    <q:set name="hits" value="0" type="number" />
    <q:set name="punches" value="0" type="number" />
    <q:set name="later" value="0" type="number" />
    <q:set name="seen" value="0" type="number" />
    <qg:when condition="{{punches >= 2}}"><q:set name="seen" value="{{seen + ticks()}}" /></qg:when>
    <qg:tilemap tileset="k">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    </qg:tilemap>
    <qg:character id="a" controller="fighter" sheet="c" x="100" y="150" hitbox="16x24" />
    <qg:character id="b" controller="fighter" player="2" sheet="c" x="200" y="150" hitbox="16x24" />
    <qg:on-input action="punch">
      <q:set name="hits" value="{{hits + 1}}" />
      <q:set name="punches" value="{{punches + 1}}" />
      <qg:set-tile col="{{int(punches)}}" row="0" tile="5" />
      <qg:after ticks="20"><q:set name="later" value="{{later + ticks()}}" /></qg:after>
      <qg:tween target="b" property="tint" from="#ff0000" to="#ffffff" seconds="0.5" />
      <qg:tween target="b" property="scale" to="1.5" seconds="0.25" yoyo="true" repeat="1">
        <qg:on-end><q:set name="hits" value="{{hits + 10}}" /></qg:on-end>
      </qg:tween>
    </qg:on-input>
  </qg:scene>
</q:application>
'''

ONE = [('punch', 30, 32), ('punch', 75, 77), ('punch', 120, 122)]
TWO = [('right', 20, 60), ('left', 90, 140)]


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp('rollback-tweens') / 'fight.q'
    src.write_text(FIGHT, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def test_tweens_and_tiles_roll_back_and_end_where_one_replay_does(project, godot):
    a, b = replay_peers(project, 200, [tape_from_holds(ONE), tape_from_holds(TWO)], binary=godot,
                        latency_ms=[120, 30], net_report=True)
    assert a['_net']['rollbacks'] > 0 and b['_net']['rollbacks'] > 0      # both guessed wrong, went back
    assert a['fight'] == b['fight']
    fight = a['fight']
    assert fight['hits'] == 33.0                                          # three punches, three pulses ended
    assert fight['tiles'] == {'1,0': 5, '2,0': 5, '3,0': 5}
    assert fight['later'] > 3 * 50 and fight['seen'] > 75                # three delays ran; the second punch seen
    # alone, with the second player's keys as its own actions and both a delay late
    holds = ONE + [(f'p2_{action}', s, e) for action, s, e in TWO]
    alone = replay(project, 200, binary=godot,
                   tape=tape_from_holds([(x, s + DELAY, e + DELAY) for x, s, e in holds]))
    assert alone['fight'] == fight
