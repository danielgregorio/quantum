"""2D lights and shadows (PLAN_GAMES_3.md, Phase 6), with Delve's vault that asked for them.

A scene with ambient= is dark: what no qg:light reaches is that colour. A qg:light in a scene is at a place;
on a character or a prefab it goes with it (a lantern). With shadows="true" the solid tiles stop it: a wall is
lit and casts its shadow past its far side, and a wall opened (qg:set-tile) lets the light through.
flicker= follows the game's ticks, so a replay's frames are the same every time. Only seen: nothing the game
reads changes, which the Delve tests' stored run says (tests/godot/test_godot_delve.py).

Checked in rendered frames (xvfb), as test_godot_play.py's frame is.
"""

import json
from pathlib import Path

import pytest
from PIL import Image

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession

REPO = Path(__file__).resolve().parents[2]
DELVE = REPO / 'projects' / 'delve' / 'delve.q'

FLOOR = ','.join(['0'] * 18)
ROW_WITH_PILLAR = ','.join(['5' if c == 7 else '0' for c in range(18)])
CAVE = f"""<q:application id="cave" type="game">
  <qg:tileset name="tiles" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="people" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:input action="open" keys="O" />
  <qg:scene name="cave" width="324" height="180" background="#808080" ambient="#000000">
    <qg:tilemap tileset="tiles" collision="true">
{FLOOR}
{FLOOR}
{FLOOR}
{ROW_WITH_PILLAR}
{ROW_WITH_PILLAR}
{ROW_WITH_PILLAR}
{FLOOR}
{FLOOR}
{FLOOR}
{FLOOR}
    </qg:tilemap>
    <qg:light x="90" y="81" radius="120" shadows="true" />
    <qg:light x="270" y="140" radius="30" color="#ff8040" flicker="1" />
    <qg:character id="hero" controller="topdown" sheet="people" frame="0" x="250" y="40" hitbox="14x14">
      <qg:light radius="24" />
    </qg:character>
    <qg:on-input action="open">
      <qg:set-tile col="7" row="3" tile="0" /><qg:set-tile col="7" row="4" tile="0" /><qg:set-tile col="7" row="5" tile="0" />
    </qg:on-input>
  </qg:scene>
</q:application>
"""


def _bright(image: Image.Image, box) -> float:
    """How bright a part of a frame is, on average (0 to 255)."""
    part = image.crop(box).convert('L')
    colours = part.getcolors(part.width * part.height)
    return sum(n * v for n, v in colours) / (part.width * part.height)


@pytest.fixture(scope='module')
def cave(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    folder = tmp_path_factory.mktemp('cave')
    (folder / 'cave.q').write_text(CAVE, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(folder / 'cave.q')), str(folder / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


@pytest.fixture(scope='module')
def frames(cave, godot, tmp_path_factory) -> dict:
    shots = tmp_path_factory.mktemp('shots')
    out = {}
    with PlaySession(cave, binary=godot, frames=True) as game:
        game.act(ticks=10)
        out['first'] = Image.open(game.frame(shots / 'first.png')['frame']).convert('RGB')
        game.act(ticks=7)
        out['later'] = Image.open(game.frame(shots / 'later.png')['frame']).convert('RGB')
        game.act(tap=['open'], ticks=3)
        out['opened'] = Image.open(game.frame(shots / 'opened.png')['frame']).convert('RGB')
    with PlaySession(cave, binary=godot, frames=True) as game:                   # the same ticks again
        game.act(ticks=10)
        out['again'] = Image.open(game.frame(shots / 'again.png')['frame']).convert('RGB')
    return out


# the light at (90, 81); the pillar is column 7 (x 126 to 144), rows 3 to 5 (y 54 to 108)
NEAR, FAR = (60, 70, 80, 90), (300, 10, 320, 30)
BEHIND, BESIDE = (160, 70, 180, 90), (90, 140, 110, 160)        # 80 px from the light: behind the pillar, below it
FACE, PAST = (127, 60, 131, 100), (146, 60, 150, 100)           # the pillar's side facing the light; just past it


def test_a_light_in_a_dark_scene(frames):
    assert _bright(frames['first'], FAR) < 3                                 # ambient black: nothing
    assert _bright(frames['first'], NEAR) > 60                               # the light's pool


def test_a_wall_stops_the_light_and_is_lit_on_its_face(frames):
    behind, beside = _bright(frames['first'], BEHIND), _bright(frames['first'], BESIDE)
    assert beside > 20 and behind < beside / 3                               # its shadow
    assert _bright(frames['first'], FACE) > 3 * _bright(frames['first'], PAST) + 20  # the wall lit, its shadow past it


def test_a_wall_opened_lets_the_light_through(frames):
    assert _bright(frames['opened'], BEHIND) > 3 * _bright(frames['first'], BEHIND) + 10


def test_a_lantern_goes_with_its_character(frames):
    assert _bright(frames['first'], (243, 33, 257, 47)) > 30                 # around the hero at (250, 40)


def test_a_flame_flickers_the_same_in_every_run(frames):
    flame = (255, 125, 285, 155)
    assert frames['first'].crop(flame).tobytes() == frames['again'].crop(flame).tobytes()
    assert frames['first'].crop(flame).tobytes() != frames['later'].crop(flame).tobytes()


def test_delves_vault_is_dark_but_where_it_is_lit(godot, tmp_path):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(DELVE)), str(tmp_path / 'godot'),
                            source_dir=str(DELVE.parent)))
    saved = json.loads((Path(__file__).parent / 'playtests' / 'delve.json').read_text())
    tape = {k: v for k, v in saved['tape'].items() if int(k) < 2900}         # the stored run, in crypt 3
    with PlaySession(out, binary=godot, frames=True) as game:
        seen = game.restore(dict(game.snapshot(), ticks=2900, tape=tape))
        assert seen['scene'] == 'crypt-3'
        vault = Image.open(game.frame(tmp_path / 'vault.png')['frame']).convert('RGB')
    lantern = seen['state']['nodes']['p1']
    x, y = round(lantern['x']), round(lantern['y'])
    around_the_delver = _bright(vault, (x + 8, y - 6, x + 20, y + 6))
    unlit = _bright(vault, (196, 186, 240, 214))                              # the walls by the vault, unlit
    assert around_the_delver > 2 * unlit and _bright(vault, (20, 56, 36, 70)) > 2 * unlit   # and by a torch
