"""qg:play with volume=, pitch= and vary= in Godot: heard, never part of the state.

A timer plays a sound every 5 ticks with a random pitch, and another plays
it plain. The state records each by its name only, so two replays are the
same whatever pitch each voice got.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay

REPO = Path(__file__).resolve().parents[2]

SOURCE = '''<q:application id="sound" type="game">
  <qg:sound name="hit" src="assets/kenney/audio/stomp.ogg" />
  <qg:scene name="main">
    <qg:timer every="5" count="8"><qg:play sound="hit" volume="-3" pitch="1.2" vary="0.3" /></qg:timer>
    <qg:timer after="3"><qg:play sound="hit" /></qg:timer>
  </qg:scene>
</q:application>
'''


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp('sound') / 'sound.q'
    src.write_text(SOURCE, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def test_varied_voices_are_heard_and_the_state_keeps_only_the_names(project, godot):
    main = replay(project, 60, binary=godot)['main']
    assert main['sounds'] == ['hit'] * 9                       # eight varied, one plain
    assert replay(project, 60, binary=godot)['main'] == main   # whatever pitch each voice had
