"""Enemies made of parts in Godot: qg:prefab ai="behavior" and its qg:behavior.

Rooms of 10x7 tiles of 18 px, walled round; inside x runs 18..162 and y
18..108. The hero is a top-down character (60 px/s, a pixel a tick); the
enemies go 30 px/s, half a pixel a tick. Each enemy is a named instance, so
the replay reports where it is and the part that moved it (`doing`).
"""

import math
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

GAME = '''<q:application id="parts" type="game">
  <qg:tileset name="dungeon" src="projects/keep/assets/dungeon.png" tile="18">
    <qg:tile frame="0" shape="none" />
  </qg:tileset>
  <qg:spritesheet name="hero" src="projects/keep/assets/hero.png" tile="24" />
  <qg:sound name="twang" src="assets/kenney/audio/stomp.ogg" />
  <q:set name="scared" value="false" type="boolean" />
{prefabs}
  <qg:scene name="room" width="180" height="126">
{state}
    <qg:tilemap tileset="dungeon" collision="true">
{map}
    </qg:tilemap>
    <qg:character id="hero" controller="topdown" sheet="hero" frame="0" x="{hx}" y="{hy}" hitbox="12x12" />
{things}
  </qg:scene>
</q:application>
'''

OPEN = '''2,2,2,2,2,2,2,2,2,2
2,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,2
2,2,2,2,2,2,2,2,2,2'''

# a wall down the middle (x 72..90), with a gap in row 4 (y 72..90)
WALLED = '''2,2,2,2,2,2,2,2,2,2
2,1,1,1,2,1,1,1,1,2
2,1,1,1,2,1,1,1,1,2
2,1,1,1,2,1,1,1,1,2
2,1,1,1,1,1,1,1,1,2
2,1,1,1,2,1,1,1,1,2
2,2,2,2,2,2,2,2,2,2'''


def enemy(name, tag, parts):
    return (f'  <qg:prefab name="{name}" tag="{tag}" sheet="dungeon" frame="9" hitbox="12x12" ai="behavior" '
            f'speed="30">\n    <qg:behavior>{parts}</qg:behavior>\n  </qg:prefab>')


def build(tmp_path_factory, godot, name, prefabs, things, room=OPEN, hero=(135, 99), state=''):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp(name) / f'{name}.q'
    src.write_text(GAME.format(prefabs='\n'.join(prefabs), things='\n'.join(things), map=room, hx=hero[0],
                               hy=hero[1], state=state), encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def at(project, godot, ticks, holds=()):
    return replay(project, ticks, tape_from_holds(list(holds)), binary=godot)['room']


def apart(a, b):
    return math.dist((a['x'], a['y']), (b['x'], b['y']))


# --- a guard: patrols until the hero comes within sight, then goes for it ---

@pytest.fixture(scope='module')
def guards(tmp_path_factory, godot):
    return build(tmp_path_factory, godot, 'guards', [
        enemy('Guard', 'guard', '<qg:seek target="hero" sight="50" way="straight" /><qg:patrol heading="down" />'),
        enemy('Pacer', 'pacer', '<qg:patrol heading="right" distance="36" />'),
    ], ['    <qg:instance prefab="Guard" name="guard" x="45" y="27" />',
        '    <qg:instance prefab="Pacer" name="pacer" x="45" y="81" />'])


def test_with_nothing_in_sight_the_next_part_moves_it(guards, godot):
    room = at(guards, godot, 60)
    assert room['named']['guard'] == {'x': 45.0, 'y': 57.0, 'doing': 'patrol'}
    turned = at(guards, godot, 200)['named']['guard']
    assert turned['doing'] == 'patrol' and 70 < turned['y'] < 102     # down to the wall (102), and back up


def test_a_patrol_turns_after_its_distance(guards, godot):
    assert at(guards, godot, 72)['named']['pacer']['x'] == pytest.approx(81, abs=0.01)
    assert at(guards, godot, 144)['named']['pacer']['x'] == pytest.approx(45, abs=0.01)


def test_once_the_hero_comes_within_sight_it_seeks(guards, godot):
    room = at(guards, godot, 200, [('left', 1, 70)])               # the hero walks to (65, 99)
    guard = room['named']['guard']
    assert guard['doing'] == 'seek'
    assert apart(guard, room['nodes']['hero']) < 16                  # up against the hero


# --- line of sight: one does not see through the wall, one notices through it ---

@pytest.fixture(scope='module')
def walled(tmp_path_factory, godot):
    state = '''    <q:set name="far" value="0" type="number" />
    <q:set name="seen" value="true" type="boolean" />
    <q:set name="met" value="false" type="boolean" />
    <qg:timer every="1">
      <q:set name="far" value="{round(distance(hero, nearest(hero, 'watcher')))}" />
      <q:set name="seen" value="{sees(hero, nearest(hero, 'watcher'))}" />
      <q:set name="met" value="{sees(hero, nearest(hero, 'hound'))}" />
    </qg:timer>'''
    return build(tmp_path_factory, godot, 'walled', [
        enemy('Watcher', 'watcher', '<qg:seek target="hero" sight="100" /><qg:stand />'),
        enemy('Hound', 'hound', '<qg:seek target="hero" sight="100" through-walls="true" /><qg:stand />'),
    ], ['    <qg:instance prefab="Watcher" name="watcher" x="45" y="45" />',
        '    <qg:instance prefab="Hound" name="hound" x="45" y="45" />'], room=WALLED, hero=(117, 45), state=state)


def test_a_wall_hides_the_hero_unless_it_notices_through_walls(walled, godot):
    room = at(walled, godot, 300)
    assert room['named']['watcher'] == {'x': 45.0, 'y': 45.0, 'doing': 'stand'}
    hound = room['named']['hound']
    assert hound['doing'] == 'seek' and apart(hound, room['nodes']['hero']) < 16   # round by the gap


def test_distance_nearest_and_sees_in_expressions(walled, godot):
    first = at(walled, godot, 2)
    assert first['far'] == 72 and first['seen'] is False and first['met'] is False
    assert at(walled, godot, 300)['met'] is True                      # the hound came round to the hero's side


# --- when=: a coward that comes on until it is scared, and an archer ---

@pytest.fixture(scope='module')
def coward(tmp_path_factory, godot):
    state = '    <qg:timer after="60"><q:set name="scared" value="true" /></qg:timer>'
    return build(tmp_path_factory, godot, 'coward', [
        enemy('Coward', 'coward', '<qg:flee from="hero" sight="200" when="{scared}" />'
                                  '<qg:seek target="hero" sight="200" />'),
    ], ['    <qg:instance prefab="Coward" name="coward" x="45" y="63" />'], hero=(135, 63), state=state)


def test_when_picks_the_part(coward, godot):
    before = at(coward, godot, 59)['named']['coward']
    assert before['doing'] == 'seek' and before['x'] == pytest.approx(45 + 29.5, abs=0.01)
    after = at(coward, godot, 120)['named']['coward']
    assert after['doing'] == 'flee' and after['x'] < before['x'] - 20


@pytest.fixture(scope='module')
def archer(tmp_path_factory, godot):
    return build(tmp_path_factory, godot, 'archer', [
        enemy('Archer', 'archer', '<qg:keep-distance from="hero" min="40" max="60" />'
                                  '<qg:shoot prefab="Arrow" at="hero" every="40" range="100" sound="twang" />'),
        '  <qg:prefab name="Arrow" tag="arrow" sheet="dungeon" frame="9" hitbox="4x4" ai="fly" speed="120" '
        'walls="stop" />',
    ], ['    <qg:instance prefab="Archer" name="archer" x="100" y="63" />'], hero=(90, 63))


def test_keep_distance_backs_off_then_holds(archer, godot):
    archer_ = at(archer, godot, 120)['named']['archer']
    assert archer_['doing'] == 'keep-distance' and archer_['y'] == 63.0
    assert archer_['x'] == pytest.approx(130, abs=0.1)                # 40 from the hero, and still
    assert at(archer, godot, 160)['named']['archer']['x'] == archer_['x']


def test_shoot_fires_at_the_target_every_so_often(archer, godot):
    room = at(archer, godot, 130)
    assert room['sounds'].count('twang') == 4                         # ticks 1, 41, 81 and 121
    arrows = [w for w in room['where'] if w[0] == 'arrow']
    assert arrows and all(w[2] == 63.0 and w[1] < 130 for w in arrows)   # flying left, at the hero
