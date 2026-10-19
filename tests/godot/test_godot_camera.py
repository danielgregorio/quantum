"""qg:camera in Godot: a dead zone, a look-ahead, several followed and fitted.

Three small games, each a top-down character in an open field (no tilemap:
bounds="none") walking right at 60 px/s, one pixel a tick. The play
protocol reports the camera as a screen view: where the screen looks
(its centre) and how close.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession

REPO = Path(__file__).resolve().parents[2]

GAME = '''<q:application id="cam" type="game">
  <qg:spritesheet name="hero" src="projects/keep/assets/hero.png" tile="24" />
  <qg:scene name="main" width="256" height="224">
    <qg:character id="hero" controller="topdown" sheet="hero" frame="0" x="100" y="112" hitbox="12x12" speed="60" />
    {extra}
    <qg:camera follow="{follow}" bounds="none" {camera} />
  </qg:scene>
</q:application>
'''


def build(tmp_path_factory, godot, name, camera, follow='hero', extra=''):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp(name) / f'{name}.q'
    src.write_text(GAME.format(camera=camera, follow=follow, extra=extra), encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def camera(obs):
    return PlaySession.screen(obs, 'camera')


def walk(project, godot, ticks):
    game = PlaySession(project, binary=godot)
    try:
        return [camera(game.act(hold=['right'], ticks=t)) for t in ticks]
    finally:
        game.close()


def test_a_dead_zone_lets_the_character_move_before_the_camera_does(tmp_path_factory, godot):
    project = build(tmp_path_factory, godot, 'dead', 'dead-zone="64x64"')
    still, moved = walk(project, godot, [30, 30])
    assert still['x'] == 100.0                     # 30 px right: inside the box's half width of 32
    assert moved['x'] == pytest.approx(160 - 32, abs=1.5)   # 60 px: the camera trails it by half the box
    assert moved['y'] == 112.0 and moved['zoom'] == 1.0


def test_lead_looks_ahead_the_way_it_goes(tmp_path_factory, godot):
    project = build(tmp_path_factory, godot, 'lead', 'lead="40" zoom="2"')
    first, settled = walk(project, godot, [6, 60])
    assert first['x'] > 106                        # already ahead of the character
    hero_x = 100 + 66
    assert settled['x'] == pytest.approx(hero_x + 40, abs=1.5)   # 40 px ahead once it has turned
    assert settled['zoom'] == 2.0


def test_several_followed_are_kept_on_the_screen(tmp_path_factory, godot):
    # a second character far to the right; both walk right with the same keys
    project = build(tmp_path_factory, godot, 'fit', 'fit="true" zoom-min="0.25"', follow='hero, far',
                    extra='<qg:character id="far" controller="topdown" sheet="hero" frame="0" x="700" y="112" '
                          'hitbox="12x12" speed="60" />')
    (seen,) = walk(project, godot, [1])
    assert seen['x'] == pytest.approx((101 + 701) / 2, abs=1.5)   # their middle
    assert 0.25 <= seen['zoom'] < 0.5                              # 600 px apart in a 256 px wide screen
