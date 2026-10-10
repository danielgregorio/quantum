"""qg:menu in Godot: keys and the pointer choose, the same way in a replay as with a mouse.

A small game: a menu of three buttons (one shown only once `unlocked`, one
with a label read from the state) and a field, and the state the buttons
change. The buttons are stacked in the centre of a 320x240 scene.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import cursor_at, replay, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

SOURCE = '''<q:application id="menus" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <q:set name="player_name" value="anon" />
  <qg:scene name="title" width="320" height="240">
    <q:set name="clicks" value="0" type="number" />
    <q:set name="unlocked" value="false" type="boolean" />
    <qg:menu size="16">
      <qg:button label="{'Clicked ' + str(clicks)}"><q:set name="clicks" value="{clicks + 1}" /></qg:button>
      <qg:button label="Unlock"><q:set name="unlocked" value="true" /></qg:button>
      <qg:button label="Play" if="{unlocked}"><qg:goto-scene name="play" /></qg:button>
      <qg:field label="Name" bind="player_name" />
    </qg:menu>
  </qg:scene>
  <qg:scene name="play" />
</q:application>
'''


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp('menus') / 'menus.q'
    src.write_text(SOURCE, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def run(project, ticks, holds=(), cursor=()):
    tape = tape_from_holds(list(holds))
    for tick, x, y in cursor:
        cursor_at(tape, tick, x, y)
    state = replay(project, ticks, tape=tape)
    scene = next(iter(state))
    return scene, state[scene]


def test_select_chooses_the_focused_button(godot, project):
    _, s = run(project, 20, [('select', 5, 7), ('select', 10, 12)])
    assert s['clicks'] == 2 and s['menus'] == [0]


def test_down_moves_the_focus_and_skips_a_hidden_button(godot, project):
    # Clicked, Unlock, (Play hidden), Name: down twice from Clicked is the field, a third time wraps
    _, s = run(project, 30, [('down', 5, 7), ('down', 10, 12)])
    assert s['menus'] == [3]
    _, s = run(project, 30, [('down', 5, 7), ('down', 10, 12), ('down', 15, 17)])
    assert s['menus'] == [0]


def test_a_shown_button_once_its_condition_holds(godot, project):
    scene, s = run(project, 40, [('down', 5, 7), ('select', 10, 12), ('down', 15, 17), ('select', 20, 22)])
    assert scene == 'play'


def test_the_pointer_focuses_and_a_click_chooses_what_is_under_it(godot, project):
    # the buttons are stacked around the scene's centre (160, 120); find the first one from the top
    for y in range(80, 130, 4):
        scene, s = run(project, 20, [('select', 10, 12), ('click', 10, 12)], [(3, 160, y)])
        if s.get('clicks') == 1:
            break
    else:
        pytest.fail('no click on the first button between y=80 and y=130')
    assert s['menus'] == [0]
    # a click where there is no button chooses nothing, whatever has the focus
    _, s = run(project, 20, [('select', 10, 12), ('click', 10, 12)], [(3, 10, 10)])
    assert s['clicks'] == 0
    # but Enter chooses the focused button wherever the pointer rests: a page clicked to give the game
    # the keyboard leaves the pointer off the buttons
    _, s = run(project, 20, [('select', 10, 12)], [(3, 10, 10)])
    assert s['clicks'] == 1
