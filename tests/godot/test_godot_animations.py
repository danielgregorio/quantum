"""Animations with events in Godot: one-shots, their end, and qg:play-animation.

A small game: a thing whose only animation plays once (3 frames at 30 fps:
2 ticks a frame) and destroys it as it ends; and a top-down character who,
on tick 10, is made to wave (3 frames at 10 fps: 6 ticks a frame) while it
walks right the whole time. The walk would take the animation back at once
if a played animation did not hold until it ended: then the wave would never
end and its handler never run.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession
from quantum.runtime.godot_replay import replay, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

SOURCE = '''<q:application id="anims" type="game">
  <q:set name="popped" value="0" type="number" />
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="hero" src="projects/keep/assets/hero.png" tile="24" />
  <qg:prefab name="Pop" tag="pop" sheet="k" frame="1" hitbox="8x8">
    <qg:animation name="walk" frames="1,2,3" fps="30" loop="false" />
    <qg:on-animation-end name="walk">
      <q:set name="popped" value="{popped + 1}" />
      <qg:destroy target="me" />
    </qg:on-animation-end>
  </qg:prefab>
  <qg:scene name="main" width="200" height="150">
    <q:set name="waved" value="0" type="number" />
    <qg:character id="hero" controller="topdown" sheet="hero" frame="0" x="40" y="40" hitbox="12x12">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:animation name="wave" frames="7,8,9" fps="10" loop="false" />
      <qg:on-animation-end name="wave"><q:set name="waved" value="{waved + 1}" /></qg:on-animation-end>
    </qg:character>
    <qg:instance prefab="Pop" name="pop" x="100" y="100" />
    <qg:timer after="10"><qg:play-animation target="hero" name="wave" /></qg:timer>
  </qg:scene>
</q:application>
'''

WALKING = tape_from_holds([('right', 1, 200)])


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp('anims') / 'anims.q'
    src.write_text(SOURCE, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def test_a_one_shot_plays_once_and_its_end_runs(project, godot):
    early = replay(project, 4, WALKING, binary=godot)['main']
    assert early['things'] == {'pop': 1} and early['game']['popped'] == 0      # on its second frame
    later = replay(project, 30, WALKING, binary=godot)['main']
    assert later['things'] == {} and later['game']['popped'] == 1               # ended once, and went


def test_a_played_animation_holds_until_it_ends_whatever_the_body_does(project, godot):
    assert replay(project, 20, WALKING, binary=godot)['main']['waved'] == 0       # still waving
    main = replay(project, 60, WALKING, binary=godot)['main']
    assert main['waved'] == 1                                                     # ended, though it walked
    assert main['nodes']['hero']['x'] > 80                                        # and walked all along


def test_the_end_is_an_event(project, godot):
    game = PlaySession(project, binary=godot)
    try:
        ends = []
        for _ in range(2):
            seen = game.until('event:animation-end', hold=['right'], max_ticks=60)
            ends += [(e['who'], e['animation']) for e in seen['events'] if e['kind'] == 'animation-end']
        assert ends == [('pop', 'walk'), ('hero', 'wave')]
    finally:
        game.close()
