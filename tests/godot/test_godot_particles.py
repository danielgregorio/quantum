"""qg:particles in Godot: named effects, emitted once or kept going, only seen.

A small game: a coin that a timer makes sparkle every half second, a fire
kept going on a spot, and rain across the top of the scene. The effects
must run without an error, show up as nodes, say so in the play protocol's
events, and leave the game's state exactly as it is without them.
"""

import json
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession
from quantum.runtime.godot_replay import replay

REPO = Path(__file__).resolve().parents[2]

GAME = '''<q:application id="fx" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:prefab name="Coin" tag="coin" sheet="k" frame="151" hitbox="12x12" />
  {particles}
  <qg:scene name="main" width="320" height="240">
    <q:set name="ticks" value="0" type="number" />
    <qg:instance prefab="Coin" name="coin" x="100" y="100" />
    {emitters}
    <qg:timer every="30">
      <q:set name="ticks" value="{{ticks + 1}}" />
      {emit}
    </qg:timer>
  </qg:scene>
</q:application>
'''

PARTICLES = '''<qg:particles name="sparkle" preset="sparks" color="#ffe060" amount="20" />
  <qg:particles name="flame" preset="fire" />
  <qg:particles name="rain" preset="rain" speed="300" />'''
EMITTERS = '''<qg:emitter particles="flame" x="200" y="200" />
    <qg:emitter particles="rain" x="160" y="0" width="320" />'''
EMIT = '<qg:emit particles="sparkle" at="coin" dy="-8" />'


def _build(tmp_path_factory, name, source, godot):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp(name) / f'{name}.q'
    src.write_text(source, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    return _build(tmp_path_factory, 'fx', GAME.format(particles=PARTICLES, emitters=EMITTERS, emit=EMIT), godot)


@pytest.fixture(scope='module')
def plain(godot, tmp_path_factory) -> Path:
    return _build(tmp_path_factory, 'plain', GAME.format(particles='', emitters='', emit=''), godot)


def test_the_effects_are_declared_for_the_runtime(project):
    data = json.loads((project / 'game.json').read_text())
    assert data['particles'] == {'sparkle': {'preset': 'sparks', 'color': '#ffe060', 'amount': 20},
                                 'flame': {'preset': 'fire'}, 'rain': {'preset': 'rain', 'speed': 300.0}}
    kinds = [n['kind'] for n in data['scenes']['main']['nodes']]
    assert kinds.count('emitter') == 2


def test_particles_are_only_seen(project, plain, godot):
    # the same game with and without its effects: the same state, tick for tick
    with_fx = replay(project, 200, binary=godot)['main']
    without = replay(plain, 200, binary=godot)['main']
    assert with_fx == without
    assert with_fx['ticks'] == 6


def test_an_emit_is_an_event(project, godot):
    with PlaySession(project, binary=godot) as game:
        seen = game.act(ticks=65)
        emitted = [e for e in seen['events'] if e['kind'] == 'emit']
        assert [e['particles'] for e in emitted] == ['sparkle', 'sparkle']
