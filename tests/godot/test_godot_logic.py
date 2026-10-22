"""Game logic in Godot (PLAN_GAMES_3.md, Phase 1): a delay a handler starts, a handler when a
condition turns true, functions every scene has, held actions and for how long, angles and sorting.

One small game, replayed. Jump turns a power on for a second; a second jump before it runs out
starts the count again (qg:after name=). Fire is held and let go: how long it was held is the
charge. Down puts off, for each coin, its end by a quarter of a second more than the last; the
scene's qg:when sees the last one go, once, and calls a q:function of the game. A second scene
has the same function, and a prefab's handler calls it too. A pause holds the clock.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

LOGIC = '''<q:application id="logic" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:input action="fire" keys="J" />
  <q:set name="log" value="[]" type="array" />
  <q:set name="score" value="0" type="number" />
  <q:function name="note" params="what">
    <q:set name="log" value="{log + [what + ' at ' + str(ticks())]}" />
  </q:function>
  <q:function name="gain" params="n">
    <q:set name="score" value="{score + n}" />
    <q:call function="note" args="{'gain ' + str(n)}" />
  </q:function>
  <qg:prefab name="Coin" tag="coin" sheet="k" frame="151" hitbox="12x12" />
  <qg:prefab name="Spark" tag="spark" sheet="k" frame="151" hitbox="4x4" ai="fly" heading="right" speed="120">
    <qg:on-collision with="coin">
      <q:call function="note" args="{'a spark, coins ' + str(count('coin'))}" />
      <qg:destroy target="me" />
    </qg:on-collision>
  </qg:prefab>
  <qg:scene name="main" width="320" height="240">
    <q:set name="power" value="false" type="boolean" />
    <q:set name="charge" value="0" type="number" />
    <q:set name="holding" value="0" type="number" />
    <q:set name="strong" value="0" type="number" />
    <q:set name="angle" value="{atan2(1, 1)}" type="number" />
    <q:set name="up" value="{atan2(-1, 0)}" type="number" />
    <q:set name="s" value="{sin(90)}" type="number" />
    <q:set name="c" value="{cos(180)}" type="number" />
    <q:set name="order" value="{sort([3, 1, 2])}" type="array" />
    <q:set name="down" value="{sort(['b', 'c', 'a'], true)}" type="array" />
    <q:set name="cleared" value="0" type="number" />
    <q:set name="paused_at" value="0" type="number" />
    <qg:instance prefab="Coin" name="c1" x="200" y="40" />
    <qg:instance prefab="Coin" name="c2" x="240" y="40" />
    <qg:instance prefab="Coin" name="c3" x="280" y="40" />
    <qg:instance prefab="Spark" x="150" y="40" />
    <qg:on-input action="jump">
      <q:set name="power" value="true" />
      <qg:after seconds="1" name="power">
        <q:set name="power" value="false" />
        <q:call function="note" args="'power off'" />
      </qg:after>
    </qg:on-input>
    <qg:on-input action="fire">
      <qg:after ticks="5"><q:set name="holding" value="{pressed_for('fire')}" /></qg:after>
    </qg:on-input>
    <qg:on-input action="fire" on="release">
      <q:set name="charge" value="{pressed_for('fire')}" />
      <q:set name="strong" value="{strength('fire') + (1 if pressing('fire') else 0)}" />
    </qg:on-input>
    <qg:on-input action="down">
      <q:set name="n" value="0" />
      <qg:for-each tag="coin" var="coin">
        <q:set name="n" value="{n + 15}" />
        <qg:after ticks="{n}">
          <q:call function="note" args="{'gone ' + coin.name}" />
          <qg:destroy target="coin" />
        </qg:after>
      </qg:for-each>
    </qg:on-input>
    <qg:when condition="{count('coin') == 0}">
      <q:set name="cleared" value="{cleared + 1}" />
      <q:call function="gain" args="100" />
    </qg:when>
    <qg:on-input action="cancel">
      <q:if condition="{paused()}">
        <qg:resume />
        <q:else>
          <q:set name="paused_at" value="{ticks()}" />
          <qg:pause />
        </q:else>
      </q:if>
    </qg:on-input>
  </qg:scene>
  <qg:scene name="other" width="320" height="240">
    <qg:timer after="1"><q:call function="gain" args="1" /></qg:timer>
  </qg:scene>
</q:application>
'''

# jump at 10 and again at 40: the power goes off a second after the second, at 100, not at 70;
# fire held from 120 to 150; down at 200 (the coins go 15, 30 and 45 ticks later);
# cancel at 300 pauses for 60 ticks, a jump at 310 waits with the scene
HOLDS = [('jump', 10, 12), ('jump', 40, 42), ('fire', 120, 150), ('down', 200, 202),
         ('cancel', 300, 302), ('jump', 310, 312), ('cancel', 360, 362)]


@pytest.fixture(scope='module')
def logic(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp('logic') / 'logic.q'
    src.write_text(LOGIC, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


@pytest.fixture(scope='module')
def run(logic, godot) -> dict:
    return replay(logic, 480, tape=tape_from_holds(HOLDS), binary=godot)['main']


def test_a_second_delay_of_the_same_name_starts_the_count_again(run):
    offs = [int(e.split()[-1]) for e in run['game']['log'] if e.startswith('power off')]
    assert len(offs) == 2                     # the jump at 10 is replaced by the one at 40; then the one at 310
    assert 95 <= offs[0] <= 105               # a second after 40, not after 10


def test_how_long_an_action_was_held(run):
    assert run['holding'] == 6.0              # its first tick counts 1; a delay five ticks on reads 6
    assert run['charge'] == 30.0              # held from 120 to 150, read on the tick it is let go
    assert run['strong'] == 0.0               # let go: no strength, not pressing


def test_angles_in_degrees_and_sort(run):
    assert run['angle'] == pytest.approx(45.0)
    assert run['up'] == pytest.approx(-90.0)  # up the screen
    assert run['s'] == pytest.approx(1.0) and run['c'] == pytest.approx(-1.0)
    assert run['order'] == [1.0, 2.0, 3.0]
    assert run['down'] == ['c', 'b', 'a']


def test_the_delays_keep_what_their_names_were_and_when_runs_once(run):
    log = run['game']['log']
    gone = [e for e in log if e.startswith('gone')]
    assert [e.split()[1] for e in gone] == ['c1', 'c2', 'c3']
    ticks = [int(e.split()[-1]) for e in gone]
    assert ticks[1] - ticks[0] == 15 and ticks[2] - ticks[1] == 15
    assert run['cleared'] == 1.0              # the last coin gone: once, though no coin stays after
    assert 'gain 100 at %d' % ticks[2] in log   # read on the tick the last delay ran, after it
    assert run['game']['score'] == 100.0


def test_a_prefab_s_handler_calls_a_function_of_the_game(run):
    assert [e for e in run['game']['log'] if e.startswith('a spark')][0].startswith('a spark, coins 3 at ')


def test_a_pause_holds_the_clock(run):
    offs = [int(e.split()[-1]) for e in run['game']['log'] if e.startswith('power off')]
    # the jump at 310 came while paused: the scene's on-input still runs, its delay waits for the clock,
    # which stood from the pause (at paused_at) to the resume, 60 ticks later
    assert offs[1] == pytest.approx(run['paused_at'] + 60, abs=3)


def test_the_same_tape_gives_the_same_game(logic, godot, run):
    again = replay(logic, 480, tape=tape_from_holds(HOLDS), binary=godot)['main']
    assert again == run
