"""Characters block each other (PLAN_GAMES_3.md, Phase 6): two bodies do not pass through each other.

A character is a body on the physics layer that tiles and solids are on, and it stops at the other characters
as at a wall: a platformer walks up to its partner and no further, and lands on its head and stands there (a
co-op platformer's step up); a top-down walker stops at another. Fighters keep their own rule (they do not
cross on the ground, tests/godot/test_godot_arena.py), and Rally's cars bump (tests/godot/test_godot_rally.py).
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

HEAD = """<q:application id="coop" type="game">
  <qg:tileset name="tiles" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="people" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:input action="left" keys="Left" player="2" />
  <qg:input action="right" keys="Right" player="2" />
  <qg:input action="up" keys="Up" player="2" />
  <qg:input action="down" keys="Down" player="2" />
  <qg:input action="jump" keys="RShift" player="2" />
"""
ROW = ','.join(['1'] * 18)
OPEN = ','.join(['0'] * 18)
LEDGE = HEAD + f"""  <qg:scene name="ledge" width="320" height="180">
    <qg:tilemap tileset="tiles" collision="true">
{ROW}
{chr(10).join([OPEN] * 8)}
{ROW}
    </qg:tilemap>
    <qg:character id="p1" controller="platformer" player="1" sheet="people" x="100" y="140" hitbox="14x20" />
    <qg:character id="p2" controller="platformer" player="2" sheet="people" frame="2" x="200" y="140" hitbox="14x20" />
  </qg:scene>
</q:application>
"""
YARD = HEAD + """  <qg:scene name="yard" width="320" height="180">
    <qg:character id="a" controller="topdown" player="1" sheet="people" x="100" y="90" hitbox="14x14" />
    <qg:character id="b" controller="topdown" player="2" sheet="people" frame="2" x="160" y="90" hitbox="14x14" />
  </qg:scene>
</q:application>
"""


@pytest.fixture(scope='module')
def coop(tmp_path_factory, godot):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    out = {}
    for name, text in (('ledge', LEDGE), ('yard', YARD)):
        folder = tmp_path_factory.mktemp(name)
        (folder / 'coop.q').write_text(text, encoding='utf-8')
        app = QuantumParser(use_cache=False).parse_file(str(folder / 'coop.q'))
        out[name] = Path(compile_game(app, str(folder / 'godot'), source_dir=str(REPO)))
        assert check_project(out[name], binary=godot) == []
    return out


def test_a_platformer_stops_at_its_partner_and_stands_on_its_head(coop, godot):
    walked = replay(coop['ledge'], 90, tape=tape_from_holds([('right', 30, 90)]))['ledge']['nodes']
    assert walked['p1']['x'] == 186.0 and walked['p2']['x'] == 200.0       # 14 px apart: side by side
    hopped = replay(coop['ledge'], 160, tape=tape_from_holds([('right', 30, 100), ('jump', 90, 160)]))
    p1, p2 = hopped['ledge']['nodes']['p1'], hopped['ledge']['nodes']['p2']
    assert abs(p1['y'] - (p2['y'] - 20)) < 0.5 and abs(p1['x'] - p2['x']) < 14   # standing on its head


def test_top_down_walkers_bump(coop, godot):
    nodes = replay(coop['yard'], 90, tape=tape_from_holds([('right', 1, 90)]))['yard']['nodes']
    assert nodes['b']['x'] - nodes['a']['x'] == pytest.approx(14, abs=0.5)
