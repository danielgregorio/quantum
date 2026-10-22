"""The tags of 2026-10-21 in Godot: what a contact ends, the screen's edges, letting a key go,
every thing of a tag, slow motion, quitting, a tween's end, positions and walls in expressions,
and health on a prefab that does not move.

Two small games, replayed: in the first a walker steps onto a plate and off it, presses and lets
go of jump (each let-go dents the coins to its right, whose health and state are their own), and
walks on into a wall; a coin's tint eases back to white and then it moves, in sequence; slow
motion runs for a while; the walker asks to quit. In the second, a shot flies off the bottom of
the screen and a rock comes in at the bottom and leaves at the top.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

WALL = '\n'.join(','.join('1' if c == 16 else '0' for c in range(18)) for _ in range(14))

TAGS = f'''<q:application id="tags" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <q:set name="log" value="[]" type="array" />
  <qg:prefab name="Coin" tag="coin" sheet="k" frame="151" hitbox="12x12" health="2">
    <qg:state name="new" frame="151" initial="true" />
    <qg:state name="dented" frame="152" />
    <qg:on-damage><qg:become target="me" state="dented" /></qg:on-damage>
    <qg:on-death><q:set name="log" value="{{log + ['a coin is gone']}}" /></qg:on-death>
  </qg:prefab>
  <qg:prefab name="Spark" tag="spark" sheet="k" frame="151" hitbox="4x4" />
  <qg:scene name="main" width="320" height="240">
    <q:set name="presses" value="0" type="number" />
    <q:set name="lets" value="0" type="number" />
    <q:set name="walled" value="false" type="boolean" />
    <q:set name="ceiling" value="false" type="boolean" />
    <q:set name="quits" value="{{can_quit()}}" type="boolean" />
    <qg:tilemap tileset="k" collision="true">
{WALL}
    </qg:tilemap>
    <qg:character id="p1" controller="topdown" sheet="k" frame="0" x="40" y="120" hitbox="12x12" speed="60">
      <qg:on-collision with="plate"><q:set name="log" value="{{log + ['on the plate']}}" /></qg:on-collision>
      <qg:on-separate with="plate">
        <q:set name="log" value="{{log + ['off the plate at ' + str(round(me.x))]}}" />
      </qg:on-separate>
    </qg:character>
    <qg:zone name="plate" tag="plate" x="60" y="110" width="20" height="20" />
    <qg:instance prefab="Coin" name="c1" x="200" y="40" />
    <qg:instance prefab="Coin" name="c2" x="240" y="40" />
    <qg:instance prefab="Coin" name="c3" x="280" y="40" />
    <qg:on-input action="jump"><q:set name="presses" value="{{presses + 1}}" /></qg:on-input>
    <qg:on-input action="jump" on="release">
      <q:set name="lets" value="{{lets + 1}}" />
      <qg:spawn prefab="Spark" at="p1" dy="-20" />
      <qg:for-each tag="coin" var="c">
        <q:if condition="{{c.x > 210}}"><qg:damage target="c" amount="1" /></q:if>
      </qg:for-each>
    </qg:on-input>
    <qg:on-input action="cancel">
      <q:set name="log" value="{{log + ['quit']}}" />
      <qg:quit />
    </qg:on-input>
    <qg:timer after="2">
      <qg:time-scale scale="0.25" seconds="2" />
      <qg:tween target="c1" property="tint" from="#ff0000" to="#ffffff" seconds="0.5" trans="linear">
        <qg:on-end>
          <q:set name="log" value="{{log + ['white']}}" />
          <qg:tween target="me" property="y" to="70" seconds="0.25" trans="linear">
            <qg:on-end><q:set name="log" value="{{log + ['moved to ' + str(me.y)]}}" /></qg:on-end>
          </qg:tween>
        </qg:on-end>
      </qg:tween>
    </qg:timer>
    <qg:timer every="5">
      <q:set name="walled" value="{{p1.on_wall}}" />
      <q:set name="ceiling" value="{{p1.on_ceiling}}" />
    </qg:timer>
  </qg:scene>
</q:application>
'''

SCREEN = '''<q:application id="screen" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <q:set name="log" value="[]" type="array" />
  <qg:prefab name="Shot" tag="shot" sheet="k" frame="151" hitbox="8x8" ai="fly" heading="down" speed="120">
    <qg:on-screen-exit side="bottom"><q:set name="log" value="{log + ['the shot is out below']}" /></qg:on-screen-exit>
    <qg:on-screen-exit side="top"><q:set name="log" value="{log + ['never: it leaves below']}" /></qg:on-screen-exit>
  </qg:prefab>
  <qg:prefab name="Rock" tag="rock" sheet="k" frame="151" hitbox="8x8" ai="fly" heading="up" speed="120" />
  <qg:scene name="main" width="320" height="240">
    <qg:instance prefab="Shot" name="shot" x="100" y="200" />
    <qg:instance prefab="Rock" name="rock" x="200" y="260" />
    <qg:on-screen-exit of="shot"><q:set name="log" value="{log + ['a shot left by any edge']}" /></qg:on-screen-exit>
    <qg:on-screen-enter of="rock" side="bottom"><q:set name="log" value="{log + ['a rock came in']}" /></qg:on-screen-enter>
    <qg:on-screen-exit of="rock" side="top"><q:set name="log" value="{log + ['a rock went out']}" /></qg:on-screen-exit>
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
def tags(godot, tmp_path_factory) -> Path:
    return _compile(godot, tmp_path_factory, TAGS, 'tags')


@pytest.fixture(scope='module')
def screen(godot, tmp_path_factory) -> Path:
    return _compile(godot, tmp_path_factory, SCREEN, 'screen')


# right held from tick 1; jump pressed at 50 and let go at 60, again at 80 and 90; cancel at 100
HOLDS = [('right', 1, 400), ('jump', 50, 60), ('jump', 80, 90), ('cancel', 100, 102)]


@pytest.fixture(scope='module')
def run(tags, godot) -> dict:
    return replay(tags, 400, tape=tape_from_holds(HOLDS), binary=godot)['main']


def test_a_contact_that_ends_runs_on_separate(run):
    log = run['game']['log']
    # its sensor (2 px beyond the 12 px hitbox each side) clears the plate's right edge (x=80) at x=89
    assert log.index('on the plate') < log.index('off the plate at 89')


def test_letting_go_of_a_key_is_its_own_handler(run):
    assert run['presses'] == 2.0 and run['lets'] == 2.0
    assert run['things']['spark'] == 2                                     # spawned at the walker, a character id


def test_for_each_reaches_every_thing_of_the_tag_and_items_have_health(run):
    # the two coins right of x=210 took a hit each let-go: dented, then gone; the first is untouched
    assert run['things']['coin'] == 1 and run['game']['log'].count('a coin is gone') == 2
    assert [w for w in run['where'] if w[0] == 'coin'] == [['coin', 200.0, 70.0, 'new']]


def test_a_tween_ends_into_the_next_one(run):
    log = run['game']['log']
    assert log.index('white') < log.index('moved to 70')
    assert 'tint' not in run['named']['c1']                               # back to as drawn


def test_slow_motion_changes_no_tick(run):
    # 60 px/s is a pixel a tick, slowed or not: the walker stops at the wall at its own pace
    assert run['nodes']['p1']['x'] == 16 * 18 - 6 and run['walled'] is True and run['ceiling'] is False


def test_a_quit_in_a_replay_is_an_event_and_the_game_goes_on(run):
    assert run['game']['log'][-1] == 'quit' and run['quits'] is True


def test_the_same_tape_gives_the_same_game(tags, godot):
    tape = tape_from_holds(HOLDS)
    assert replay(tags, 120, tape=tape, binary=godot) == replay(tags, 120, tape=tape, binary=godot)


def test_slow_motion_is_seen_as_events_and_ends_by_itself(tags, godot):
    from quantum.runtime.godot_play import PlaySession
    with PlaySession(tags, binary=godot) as s:
        events = s.act(ticks=40)['events']
    scales = [(e['tick'], e['scale']) for e in events if e['kind'] == 'time-scale']
    assert [s for _, s in scales] == [0.25, 1.0]
    assert scales[1][0] - scales[0][0] == 30          # two seconds at a quarter of the speed: 30 ticks


def test_the_screen_s_edges(screen, godot):
    early = replay(screen, 40, binary=godot)['main']['game']['log']
    assert early == ['a rock came in', 'the shot is out below', 'a shot left by any edge']
    late = replay(screen, 140, binary=godot)['main']['game']['log']
    assert late == early + ['a rock went out']
