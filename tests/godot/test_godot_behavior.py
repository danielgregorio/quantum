"""qg:behavior in Godot: a character made of parts.

Two small games. In the first, a platformer controller and a body made of
qg:gravity, qg:walk and qg:jump with the same numbers stand on one floor and
take the same keys: they run, hop, jump twice and land the same, to the
pixel; then a qg:velocity throws the parts-made one up, and `parts.on_floor`
reads it in the air. In the second, a walker on both axes is stopped by the
scene's edges (qg:keep-inside), and a body that walks across comes back on
the other side (qg:wrap).
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

HEAD = '''<q:application id="{id}" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="hero" src="projects/keep/assets/hero.png" tile="24" />
'''

PLATFORMS = HEAD.format(id='parts') + '''  <qg:scene name="main" width="540" height="180">
    <q:set name="airborne" value="false" />
    <qg:tilemap tileset="k" collision="true">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1
    </qg:tilemap>
    <qg:character id="plat" controller="platformer" sheet="hero" x="290" y="146" hitbox="12x16"
                  run-speed="90" jump-height="40" air-jumps="1" gravity="800" max-fall="280" />
    <qg:character id="parts" controller="behavior" sheet="hero" x="398" y="146" hitbox="12x16">
      <qg:behavior>
        <qg:face />
        <qg:jump height="40" air="1" />
        <qg:walk speed="90" />
        <qg:gravity strength="800" max-fall="280" />
      </qg:behavior>
    </qg:character>
    <qg:timer after="300">
      <qg:velocity target="parts" y="-240" />
    </qg:timer>
    <qg:timer after="310">
      <q:set name="airborne" value="{not parts.on_floor}" />
    </qg:timer>
  </qg:scene>
</q:application>
'''

# right; a hop let go at once; a full jump with a second one in the air; left
PLATFORM_TAPE = tape_from_holds([('right', 5, 60), ('jump', 30, 33), ('jump', 90, 130), ('jump', 110, 125),
                                 ('left', 100, 170)])

FLOATERS = HEAD.format(id='floaters') + '''  <qg:scene name="main" width="200" height="150">
    <qg:character id="walker" controller="behavior" sheet="hero" x="60" y="100" hitbox="12x12">
      <qg:behavior>
        <qg:walk speed="60" axis="both" />
        <qg:keep-inside />
        <qg:face by="input" />
      </qg:behavior>
    </qg:character>
    <qg:character id="looper" controller="behavior" sheet="hero" x="100" y="20" hitbox="12x12">
      <qg:behavior>
        <qg:walk speed="120" />
        <qg:wrap />
      </qg:behavior>
    </qg:character>
  </qg:scene>
</q:application>
'''


def _build(source: str, name: str, godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp(name) / f'{name}.q'
    src.write_text(source, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


@pytest.fixture(scope='module')
def platforms(godot, tmp_path_factory) -> Path:
    return _build(PLATFORMS, 'parts', godot, tmp_path_factory)


@pytest.fixture(scope='module')
def floaters(godot, tmp_path_factory) -> Path:
    return _build(FLOATERS, 'floaters', godot, tmp_path_factory)


def test_gravity_walk_and_jump_make_the_platformer(platforms, godot):
    """The parts in any order, the same numbers: the same run, hop, double jump and landing."""
    standing = None
    for ticks in (20, 45, 100, 128, 200):
        nodes = replay(platforms, ticks, PLATFORM_TAPE, binary=godot)['main']['nodes']
        plat, parts = nodes['plat'], nodes['parts']
        assert parts['y'] == plat['y'], ticks
        assert parts['x'] - 108.0 == plat['x'], ticks
        standing = standing or plat['y']
    assert nodes['plat']['y'] == pytest.approx(standing, abs=0.02)   # landed again, both


def test_the_hop_is_lower_than_the_jump(platforms, godot):
    y = {t: replay(platforms, t, PLATFORM_TAPE, binary=godot)['main']['nodes']['parts']['y'] for t in (20, 40, 105)}
    assert y[20] - y[40] < 20                               # let go at once: a hop
    assert y[20] - y[105] > 30                              # held: near its 40 px


def test_velocity_throws_it_and_on_floor_reads_it(platforms, godot):
    main = replay(platforms, 312, PLATFORM_TAPE, binary=godot)['main']
    assert main['nodes']['parts']['y'] < main['nodes']['plat']['y'] - 10
    assert main['airborne'] is True
    nodes = replay(platforms, 420, PLATFORM_TAPE, binary=godot)['main']['nodes']
    assert nodes['parts']['y'] == nodes['plat']['y']        # and it comes down to the floor again


def test_walk_on_both_axes_stays_inside_and_wrap_comes_round(floaters, godot):
    nodes = replay(floaters, 241, tape_from_holds([('right', 1, 400), ('down', 1, 400)]), binary=godot)['main']['nodes']
    assert (nodes['walker']['x'], nodes['walker']['y']) == (194.0, 144.0)   # the corner, less half its box
    # 2 px a tick for 240 ticks from x 100: 580, which is 180 round a 200-wide scene; down does not move it
    assert nodes['looper']['x'] == pytest.approx(180.0, abs=0.05)
    assert nodes['looper']['y'] == 20.0


def test_a_diagonal_is_no_faster(floaters, godot):
    nodes = replay(floaters, 31, tape_from_holds([('right', 1, 400), ('down', 1, 400)]), binary=godot)['main']['nodes']
    # 30 ticks at 60 px/s along the diagonal: 30 px, so 21.2 on each axis
    assert nodes['walker']['x'] - 60.0 == pytest.approx(21.21, abs=0.05)
    assert nodes['walker']['y'] - 100.0 == pytest.approx(21.21, abs=0.05)
