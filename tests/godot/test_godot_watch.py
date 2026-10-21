"""Watching a networked game: qg:watch and --q-watch in Godot.

Two players on two headless Godots, and two more Godots that only watch: one
joins as the game starts, the other a few seconds into it and catches up on
the inputs so far. The watchers have no seat and press nothing; each runs the
game the players' inputs make, and ends where the players end.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay_peers, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

GAME = '''<q:application id="watched" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:multiplayer players="2" delay="2" start="field" />
  <qg:scene name="field" width="320" height="240" seed="5">
    <qg:character id="p1" controller="topdown" player="1" sheet="k" frame="0" x="40" y="40" hitbox="12x12" speed="60" />
    <qg:character id="p2" controller="topdown" player="2" sheet="k" frame="0" x="200" y="40" hitbox="12x12" speed="60" />
  </qg:scene>
</q:application>
'''


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp('watched') / 'watched.q'
    src.write_text(GAME, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def test_who_watches_sees_the_game_the_players_play(project, godot):
    tapes = [tape_from_holds([('right', 10, 100), ('down', 150, 250)]),
             tape_from_holds([('down', 20, 120), ('left', 200, 300)])]
    one, two, early, late = replay_peers(project, 400, tapes, binary=godot, watchers=[0.0, 3.0])
    field = one['field']
    assert field['nodes']['p1']['x'] > 40 and field['nodes']['p2']['x'] < 200   # both played
    assert one == two == early == late             # the same game on the four machines
