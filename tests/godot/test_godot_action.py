"""Action and aiming in Godot (PLAN_GAMES_3.md, Phase 2, the tags Siege asked for).

Three small games, replayed. In the first, a range: a shot leaves the archer at the pointer (a
qg:cursor with an id, `aim.x`), flies right, through a crate (hit on one side) and off a wall of
tiles (walls="bounce"), and back through the crate (hit on the other). Each hit squashes the crate
(scale-x, scale-y), floats a number, and draws a beam; the crate hides at its last health
(visible=), and a label over it says what it has left. Bees seek the archer from one spot, keeping
apart (spacing=); flies do the same without it. In the second, a ship steers: thrust takes it the
way it points, turning points it elsewhere, and it goes no faster than max=. In the third, a jump
pressed just before landing jumps as it lands (buffer-frames=), and without the buffer it does
not.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession
from quantum.runtime.godot_replay import cursor_at, replay, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

WALL = '\n'.join(','.join('1' if c == 15 else '0' for c in range(18)) for _ in range(14))

RANGE = f'''<q:application id="range" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="c" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:particles name="fire" preset="fire" />
  <q:set name="log" value="[]" type="array" />
  <q:function name="hit" params="crate, side">
    <q:set name="log" value="{{log + [side]}}" />
    <qg:damage target="crate" />
    <qg:emit text="{{str(crate.health)}}" at="crate" dy="-10" color="#ffe070" />
    <qg:tween target="crate" property="scale-x" to="1.5" seconds="0.05" />
    <qg:tween target="crate" property="scale-y" to="0.5" seconds="0.05" />
  </q:function>
  <qg:prefab name="Shot" tag="shot" sheet="k" frame="151" hitbox="6x6" ai="fly" speed="180" rotate="true"
             walls="bounce" lifetime="300" trail="#ffd070" />
  <qg:prefab name="Crate" tag="crate" sheet="k" frame="151" hitbox="16x16" health="4" ai="behavior" speed="0"
             particles="fire" flip-v="true" layer="2" visible="{{me.health > 1}}">
    <qg:behavior><qg:stand /></qg:behavior>
    <qg:label value="{{'HP ' + str(me.health)}}" dy="-14" />
    <qg:on-collision with="shot" side="left"><q:call function="hit" args="me, 'left'" /></qg:on-collision>
    <qg:on-collision with="shot" side="right"><q:call function="hit" args="me, 'right'" /></qg:on-collision>
    <qg:on-collision with="shot"><q:call function="hit" args="me, 'any'" /></qg:on-collision>
  </qg:prefab>
  <qg:prefab name="Bee" tag="bee" sheet="k" frame="151" hitbox="8x8" ai="behavior" speed="40" sight="400"
             spacing="20">
    <qg:behavior><qg:seek target="p1" way="straight" /></qg:behavior>
  </qg:prefab>
  <qg:prefab name="Fly" tag="fly" sheet="k" frame="151" hitbox="8x8" ai="behavior" speed="40" sight="400">
    <qg:behavior><qg:seek target="p1" way="straight" /></qg:behavior>
  </qg:prefab>
  <qg:scene name="main" width="320" height="240" y-sort="true">
    <qg:tilemap tileset="k" collision="true">
{WALL}
    </qg:tilemap>
    <qg:character id="p1" controller="topdown" sheet="c" frame="0" x="40" y="120" hitbox="12x12" speed="0">
      <qg:label value="{{'ARCHER'}}" />
    </qg:character>
    <qg:cursor id="aim" step="0" />
    <qg:instance prefab="Crate" name="crate" x="150" y="120" />
    <qg:label value="{{'RANGE'}}" x="160" y="10" />
    <qg:instance prefab="Bee" x="100" y="20" />
    <qg:instance prefab="Bee" x="101" y="20" />
    <qg:instance prefab="Bee" x="102" y="20" />
    <qg:instance prefab="Fly" x="200" y="20" />
    <qg:instance prefab="Fly" x="201" y="20" />
    <qg:on-input action="jump">
      <qg:spawn prefab="Shot" at="p1" heading="{{aim.x - p1.x}},{{aim.y - p1.y}}" />
      <qg:beam from="p1" to="aim" seconds="0.2" color="#80d0ff" />
    </qg:on-input>
  </qg:scene>
</q:application>
'''

SKY = '''<q:application id="sky" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:scene name="main" width="640" height="480">
    <q:set name="fast" value="0" type="number" />
    <qg:character id="ship" controller="behavior" sheet="k" frame="151" x="100" y="100" hitbox="12x12">
      <qg:behavior><qg:steer turn="90" thrust="120" drag="0" max="100" heading="0" /></qg:behavior>
    </qg:character>
    <qg:timer every="1"><q:set name="fast" value="{sqrt(ship.vx * ship.vx + ship.vy * ship.vy)}" /></qg:timer>
  </qg:scene>
</q:application>
'''

FLOOR = '\n'.join(['0,' * 17 + '0'] * 12 + ['1,' * 17 + '1'] * 2)

GROUND = f'''<q:application id="ground" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="c" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:sound name="jump" src="assets/kenney/audio/jump.ogg" />
  <q:set name="landed" value="[]" type="array" />
  <qg:scene name="main" width="320" height="252">
    <qg:tilemap tileset="k" collision="true">
{FLOOR}
    </qg:tilemap>
    <qg:character id="hero" controller="platformer" sheet="c" frame="0" x="60" y="180" hitbox="18x22"
                  jump-sound="jump" buffer-frames="BUFFER" />
    <qg:when condition="{{hero.on_floor}}"><q:set name="landed" value="{{landed + [ticks()]}}" /></qg:when>
  </qg:scene>
</q:application>
'''


def _compile(godot, tmp_path_factory, source: str, name: str) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp(name) / f'{name}.q'
    src.write_text(source, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


@pytest.fixture(scope='module')
def range_(godot, tmp_path_factory) -> Path:
    return _compile(godot, tmp_path_factory, RANGE, 'range')


@pytest.fixture(scope='module')
def shot(range_, godot) -> dict:
    # the pointer at the far right, level with the archer; one shot at tick 10
    tape = cursor_at(tape_from_holds([('jump', 10, 12)]), 5, 300, 120)
    return replay(range_, 200, tape=tape, binary=godot)['main']


def test_a_shot_goes_at_the_pointer_and_bounces_off_the_wall(shot):
    # out to the right, through the crate, off the wall at x=270, back through the crate
    assert shot['game']['log'] == ['right', 'left']


def test_hits_squash_the_crate_and_its_last_health_hides_it(shot):
    crate = shot['named']['crate']
    assert crate['scale'] == 1.5 and crate['scale_y'] == 0.5
    assert crate.get('hidden') is not True                  # 2 left: still shown
    assert shot['things']['crate'] == 1


def test_things_of_a_tag_keep_apart_with_spacing(shot):
    bees = sorted((x, y) for tag, x, y, *_ in shot['where'] if tag == 'bee')
    flies = sorted((x, y) for tag, x, y, *_ in shot['where'] if tag == 'fly')

    def closest(points):
        return min(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
                   for i, a in enumerate(points) for b in points[i + 1:])
    assert closest(bees) >= 15                              # a crowd, not a pile
    assert closest(flies) < 3                               # without spacing= they stay on one another


def test_a_label_a_beam_and_a_number_reach_the_play_protocol(range_, godot):
    with PlaySession(range_, binary=godot) as game:
        game.act(ticks=4, cursor=(300, 120))
        seen = game.act(tap=['jump'], ticks=100, cursor=(300, 120))
        kinds = [e['kind'] for e in seen['events']]
        assert 'beam' in kinds and 'bounce' in kinds
        assert any(e['kind'] == 'emit' and e.get('text') == '3' for e in seen['events'])
        labels = [v for v in seen['screen'] if v['kind'] == 'label']
        texts = sorted(t for v in labels for t in v['items'])
        assert texts == ['ARCHER', 'HP 3', 'RANGE']


def test_the_crate_hides_at_its_last_health(range_, godot):
    tape = cursor_at(tape_from_holds([('jump', 10, 12), ('jump', 30, 32)]), 5, 300, 120)
    # out: 3, then 2; the first shot's way back: 1, hidden (it still collides: the second's way back ends it)
    state = replay(range_, 135, tape=tape, binary=godot)['main']
    assert state['game']['log'] == ['right', 'right', 'left']
    assert state['named']['crate']['hidden'] is True


@pytest.fixture(scope='module')
def sky(godot, tmp_path_factory) -> Path:
    return _compile(godot, tmp_path_factory, SKY, 'sky')


def test_a_ship_steers_turns_and_keeps_to_its_top_speed(sky, godot):
    ahead = replay(sky, 60, tape=tape_from_holds([('up', 1, 60)]), binary=godot)['main']
    assert ahead['nodes']['ship']['x'] > 120 and ahead['nodes']['ship']['y'] == 100.0   # pointing right
    turned = replay(sky, 120, tape=tape_from_holds([('up', 1, 120), ('right', 60, 120)]), binary=godot)['main']
    assert turned['nodes']['ship']['y'] > 110                # turned clockwise: down the screen
    assert turned['fast'] <= 100.01                         # never past max=


@pytest.mark.parametrize('buffer,jumps', [(6, 2), (0, 1)])
def test_a_jump_pressed_before_landing_jumps_as_it_lands(godot, tmp_path_factory, buffer, jumps):
    project = _compile(godot, tmp_path_factory, GROUND.replace('BUFFER', str(buffer)), f'ground{buffer}')
    # where the first jump comes down: the tick it lands again
    first = replay(project, 120, tape=tape_from_holds([('jump', 20, 22)]), binary=godot)['main']
    lands = first['game']['landed'][-1]
    state = replay(project, 160, binary=godot,
                   tape=tape_from_holds([('jump', 20, 22), ('jump', lands - 3, lands - 1)]))['main']
    assert state['sounds'].count('jump') == jumps
