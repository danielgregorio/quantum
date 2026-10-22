"""Music and sounds within a scene in Godot (PLAN_GAMES_3.md, Phase 6).

`qg:music` in a handler changes the music there and then (a boss's theme as the fight starts, the scene's
own as it ends), and `qg:play sounds=` plays one of several each time. Both are what is heard only: the
game's state records the sounds as written, so a replay is the same game.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession
from quantum.runtime.godot_replay import replay, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

HALL = '''<q:application id="hall" type="game">
  <qg:sound name="calm" src="assets/kenney/audio/win.ogg" loop="true" bus="music" />
  <qg:sound name="fight" src="assets/kenney/audio/powerup.ogg" loop="true" bus="music" />
  <qg:sound name="step1" src="assets/kenney/audio/jump.ogg" />
  <qg:sound name="step2" src="assets/kenney/audio/stomp.ogg" />
  <qg:sound name="step3" src="assets/kenney/audio/block.ogg" />
  <qg:scene name="hall" width="160" height="120">
    <qg:music sound="calm" />
    <q:set name="fighting" value="false" type="boolean" />
    <qg:on-input action="jump">
      <q:if condition="{not fighting}">
        <q:set name="fighting" value="true" />
        <qg:music sound="fight" fade="0" />
      <q:else>
        <q:set name="fighting" value="false" />
        <qg:music sound="calm" fade="0.5" />
      </q:else>
      </q:if>
    </qg:on-input>
    <qg:on-input action="right"><qg:play sounds="step1, step2, step3" vary="0.1" /></qg:on-input>
  </qg:scene>
</q:application>
'''


@pytest.fixture(scope='module')
def hall(tmp_path_factory, godot):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    folder = tmp_path_factory.mktemp('hall')
    (folder / 'hall.q').write_text(HALL, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(folder / 'hall.q')), str(folder / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def test_the_music_changes_within_the_scene(hall, godot):
    with PlaySession(hall, binary=godot) as game:
        assert game.observe()['music'] == 'calm'
        fight = game.act(tap=['jump'], ticks=2)
        assert fight['music'] == 'fight' and [e['name'] for e in fight['events'] if e['kind'] == 'music'] == ['fight']
        assert game.act(tap=['jump'], ticks=2)['music'] == 'calm'


def test_one_of_several_sounds_is_heard_and_the_state_records_them_as_written(hall, godot):
    steps = [('right', t, t + 2) for t in range(1, 60, 6)]
    first = replay(hall, 70, tape=tape_from_holds(steps))['hall']
    assert first['sounds'] == ['step1, step2, step3'] * 10
    assert replay(hall, 70, tape=tape_from_holds(steps))['hall'] == first   # whichever was heard
