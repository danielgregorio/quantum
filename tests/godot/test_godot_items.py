"""What the players carry, in Godot: qg:item, gives=, opens-with=, qg:give, qg:take.

Rooms of 10x7 tiles of 18 px, walled round: inside, x runs 18..162 and y
18..108. A top-down hero (12x12, 60 px/s: a pixel a tick) walks right along
y=63. What is held is the game's state: the replay reports it under `game`,
as `q_items` (how many of each) and `q_gone` (the named things picked up or
opened, which do not come back).
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession
from quantum.runtime.godot_replay import replay, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

GAME = '''<q:application id="items" type="game">
  <qg:tileset name="dungeon" src="projects/keep/assets/dungeon.png" tile="18">
    <qg:tile frame="0" shape="none" />
  </qg:tileset>
  <qg:spritesheet name="hero" src="projects/keep/assets/hero.png" tile="24" />
  <qg:sound name="pick" src="assets/kenney/audio/stomp.ogg" />
  <qg:item name="key" label="KEY" sheet="dungeon" frame="8" sound="pick" />
  <qg:item name="gem" label="GEMS" sheet="dungeon" frame="7" max="3" />
  <qg:item name="potion" label="POTIONS" start="2" />
{prefabs}
  <qg:scene name="room" width="180" height="126">
{state}
    <qg:tilemap tileset="dungeon" collision="true">
2,2,2,2,2,2,2,2,2,2
2,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,2
2,2,2,2,2,2,2,2,2,2
    </qg:tilemap>
    <qg:character id="hero" controller="topdown" sheet="hero" frame="0" x="30" y="63" hitbox="12x12" speed="60" />
{things}
  </qg:scene>
</q:application>
'''


def build(tmp_path_factory, godot, name, prefabs, things, state=''):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp(name) / f'{name}.q'
    src.write_text(GAME.format(prefabs=prefabs, things=things, state=state), encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def at(project, godot, ticks, holds=()):
    return replay(project, ticks, tape_from_holds(list(holds)), binary=godot)['room']


# --- picking up: four gems (three at most) and a named key, then the room again ---

@pytest.fixture(scope='module')
def pickups(tmp_path_factory, godot):
    prefabs = '''  <qg:prefab name="Gem" tag="gem" sheet="dungeon" frame="7" hitbox="10x10" gives="gem" />
  <qg:prefab name="Key" tag="key" sheet="dungeon" frame="8" hitbox="10x10" gives="key" />'''
    things = '''    <qg:instance prefab="Gem" x="60" y="63" />
    <qg:instance prefab="Gem" x="75" y="63" />
    <qg:instance prefab="Gem" x="90" y="63" />
    <qg:instance prefab="Gem" x="105" y="63" />
    <qg:instance prefab="Key" name="key-1" x="125" y="63" />
    <qg:timer after="150"><qg:take item="gem" amount="2" /><qg:give item="potion" amount="5" /></qg:timer>
    <qg:timer after="200"><qg:goto-scene name="room" /></qg:timer>
    <qg:hud><qg:counter item="gem" label="GEMS" /><qg:inventory /></qg:hud>'''
    return build(tmp_path_factory, godot, 'pickups', prefabs, things)


def test_touching_picks_up_up_to_the_most_held(pickups, godot):
    room = at(pickups, godot, 120, [('right', 1, 110)])
    assert room['game']['q_items'] == {'key': 1, 'gem': 3, 'potion': 2}
    assert room['things'] == {'gem': 1}                 # the fourth gem stays: three is the most
    assert room['game']['q_gone'] == ['room/key-1']     # the key had a name: it is remembered
    assert room['sounds'] == ['pick']                   # the key's sound; the gems have none


def test_give_and_take(pickups, godot):
    room = at(pickups, godot, 160, [('right', 1, 110)])
    assert room['game']['q_items'] == {'key': 1, 'gem': 1, 'potion': 7}


def test_a_named_thing_picked_up_does_not_come_back(pickups, godot):
    room = at(pickups, godot, 260, [('right', 1, 110)])
    assert room['things'] == {'gem': 4}                 # the room built again: its gems, not its key
    assert room['game']['q_items']['key'] == 1


def test_the_hud_shows_what_is_held(pickups, godot):
    game = PlaySession(pickups, binary=godot)
    try:
        hud = PlaySession.screen(game.act(hold=['right'], ticks=110), 'hud')
    finally:
        game.close()
    assert hud['items'][0] == 'GEMS 3'
    assert hud['items'][1] == {'inventory': {'key': 1, 'gem': 3, 'potion': 2}}


# --- doors: one that spends its key, one that keeps it, and on-locked ---

@pytest.fixture(scope='module')
def doors(tmp_path_factory, godot):
    prefabs = '''  <q:set name="locked" value="0" type="number" />
  <qg:prefab name="Door" tag="door" sheet="dungeon" frame="2" hitbox="18x18" solid="true" opens-with="key">
    <qg:on-locked><q:set name="locked" value="{locked + 1}" /></qg:on-locked>
  </qg:prefab>
  <qg:prefab name="Gate" tag="gate" sheet="dungeon" frame="2" hitbox="18x18" solid="true" opens-with="key"
             keeps="true" />'''
    things = '''    <qg:instance prefab="Door" name="door-1" x="99" y="63" />
    <qg:instance prefab="Gate" name="gate-1" x="135" y="63" />
    <qg:timer after="65"><qg:give item="key" amount="2" /></qg:timer>'''
    return build(tmp_path_factory, godot, 'doors', prefabs, things)


def test_without_the_item_a_door_stays_shut_and_on_locked_runs(doors, godot):
    room = at(doors, godot, 60, [('right', 1, 60)])
    assert room['game']['locked'] == 1
    assert room['things'] == {'door': 1, 'gate': 1}
    assert room['nodes']['hero']['x'] == pytest.approx(84, abs=0.5)    # against the door (x 90..108)


def test_with_it_the_door_opens_and_spends_it_and_the_gate_keeps_it(doors, godot):
    # up against the door, back off, get two keys, and walk on through both
    room = at(doors, godot, 200, [('right', 1, 60), ('left', 61, 70), ('right', 71, 200)])
    assert room['game']['locked'] == 1
    assert room['things'] == {}
    assert room['game']['q_items']['key'] == 1           # the door took one; the gate let it be
    assert room['game']['q_gone'] == ['room/door-1', 'room/gate-1']
    assert room['nodes']['hero']['x'] > 140


# --- saved and continued: what is held, and what stays gone ---

def test_a_save_keeps_what_is_held_and_what_is_gone(tmp_path_factory, godot):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    title = '''  <qg:scene name="title" width="180" height="126">
    <qg:timer after="1">
      <q:if condition="{has_save()}"><qg:continue /><q:else><qg:goto-scene name="room" /></q:else></q:if>
    </qg:timer>
  </qg:scene>
'''
    prefabs = '''  <qg:prefab name="Gem" tag="gem" sheet="dungeon" frame="7" hitbox="10x10" gives="gem" />
  <qg:prefab name="Key" tag="key" sheet="dungeon" frame="8" hitbox="10x10" gives="key" />
''' + title
    things = '''    <qg:instance prefab="Gem" x="60" y="63" />
    <qg:instance prefab="Key" name="key-1" x="90" y="63" />
    <qg:timer after="100"><qg:save /></qg:timer>'''
    src = tmp_path_factory.mktemp('saved') / 'saved.q'
    src.write_text(GAME.format(prefabs=prefabs, things=things, state=''), encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    keep = tmp_path_factory.mktemp('saves')
    first = replay(out, 120, tape_from_holds([('right', 1, 90)]), binary=godot, persist_dir=keep)['room']
    assert first['game']['q_items'] == {'key': 1, 'gem': 1, 'potion': 2}
    again = replay(out, 20, binary=godot, persist_dir=keep)['room']        # a new run: Continue
    assert again['game']['q_items'] == {'key': 1, 'gem': 1, 'potion': 2}
    assert again['things'] == {'gem': 1}                                  # the gem is back; the key is not
