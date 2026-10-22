"""Screens of a management game in Godot (PLAN_PANDAFOOT.md, Phase 1).

A small game with what PandaFoot's screens are made of: a qg:table of the
state's rows in the HUD, a menu with a button for each row of a list
(source=, as=), two menus shown at once that share the keys, a HUD placed by
x= and y= in a box, a colour read from the state, the text functions
(fit, thousands, repeat, join), a field of a record and a key of a dictionary
set in place, and a scene seeded by the game's state (a world's number).
"""

import json
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project, run_godot, script_errors
from quantum.runtime.godot_play import PlaySession

REPO = Path(__file__).resolve().parents[2]
PROBE = Path(__file__).with_name('gd_probe.gd')

SOURCE = '''<q:application id="tables" type="game">
  <q:set name="team" value="[]" type="array" />
  <q:set name="tally" value="{ {} }" />
  <q:set name="world" value="5" type="number" />
  <q:set name="draws" value="[]" type="array" />
  <q:set name="picked" value="" />
  <qg:spritesheet name="frame" src="projects/pandafoot/assets/frame.png" tile="24" slice="8" />
  <q:function name="money" params="n">
    <q:return value="{('-$' if n < 0 else '$') + thousands(abs(n))}" />
  </q:function>
  <qg:scene name="board" width="320" height="240" seed="{world}">
    <q:set name="rolls" value="{[pick([1, 2, 3, 4, 5, 6]), pick([1, 2, 3, 4, 5, 6]), chance(0.5), round(random(0, 1000))]}" type="array" />
    <q:if condition="{len(team) == 0}">
      <q:set name="team" value="{[ {'name': 'Ana', 'goals': 3, 'pay': 1500000}, {'name': 'Bruno', 'goals': 0, 'pay': -2500}, {'name': 'Carla Cristina', 'goals': 12, 'pay': 900} ]}" />
    </q:if>
    <q:set name="draws" value="{draws + [rolls]}" />
    <qg:hud x="10" y="20" box="frame" size="10">
      <qg:text value="{'Pay ' + money(1500000) + ' ' + join(['a', 1, 2.0], '/') + ' ' + repeat('=', 3) + fit('ab', 4) + '|' + fit(7, 3, 'right') + '|' + fit('abcdef', 3)}" color="{'#ff0000' if len(team) > 3 else '#00ff00'}" />
      <qg:table source="{team}" as="p" rows="3">
        <qg:column label="Name" value="{p.name}" width="8" />
        <qg:column label="G" value="{p.goals}" width="3" align="right" color="{'#ffff00' if p.goals > 5 else ''}" />
        <qg:column label="Pay" value="{money(p.pay)}" width="11" align="right" color="#55ff55" />
      </qg:table>
    </qg:hud>
    <qg:menu x="10" y="150" source="{team}" as="p" size="10">
      <qg:button label="{fit(p.name, 6) + fit(p.goals, 3, 'right')}" if="{p.goals < 10}">
        <q:set name="p.goals" value="{p.goals + 1}" />
        <q:set name="tally" index="{p.name}" value="{(tally[p.name] if p.name in tally else 0) + 1}" />
        <q:set name="picked" value="{p.name}" />
      </qg:button>
    </qg:menu>
    <qg:menu x="200" y="150" size="10">
      <qg:button label="Add"><q:set name="team" value="{team + [ {'name': 'Davi', 'goals': 1, 'pay': 0} ]}" /></qg:button>
      <qg:button label="Next world"><q:set name="world" value="{world + 1}" /><qg:goto-scene name="board" /></qg:button>
      <qg:button label="Back world"><q:set name="world" value="{world - 1}" /><qg:goto-scene name="board" /></qg:button>
    </qg:menu>
  </qg:scene>
</q:application>
'''


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp('tables') / 'tables.q'
    src.write_text(SOURCE, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def hud(obs):
    return PlaySession.screen(obs, 'hud')['items']


def menus(obs):
    return [v for v in obs['screen'] if v['kind'] == 'menu']


def labels(menu):
    return [item['button'] for item in menu['items'] if item['shown']]


def test_a_table_shows_rows_of_the_state_in_columns(godot, project):
    with PlaySession(project, binary=godot) as game:
        items = hud(game.act(ticks=2))
        assert items[0] == 'Pay $1,500,000 a/1/2 ===ab  |  7|abc'
        assert items[1] == {'table': ['Name', 'G', 'Pay'],
                            'rows': [['Ana', '3', '$1,500,000'], ['Bruno', '0', '-$2,500'],
                                     ['Carla Cr', '12', '$900']]}   # cut to its column, as on the screen


def test_a_menu_has_a_button_for_each_row_and_runs_it_with_the_row(godot, project):
    with PlaySession(project, binary=godot) as game:
        rows, others = menus(game.act(ticks=2))
        assert labels(rows) == ['Ana     3', 'Bruno   0']          # Carla's if= is false: 12 goals
        assert rows['focus'] == 0 and others['keys'] is False     # the first menu has the keys
        chose = game.act(tap=['select'], ticks=2)
        assert chose['state']['game']['picked'] == 'Ana'
        assert chose['state']['game']['team'][0]['goals'] == 4    # p.goals set in place, in the list
        assert chose['state']['game']['tally'] == {'Ana': 1}      # a key of a dictionary
        again = game.act(tap=['select'], ticks=2)
        assert again['state']['game']['tally'] == {'Ana': 2}
        assert labels(menus(again)[0])[0] == 'Ana     5'
        assert hud(again)[1]['rows'][0] == ['Ana', '5', '$1,500,000']


def test_down_from_the_last_row_takes_the_keys_to_the_next_menu(godot, project):
    with PlaySession(project, binary=godot) as game:
        game.act(ticks=2)
        game.act(tap=['down'], ticks=2)                            # Bruno
        moved = game.act(tap=['down'], ticks=2)                    # past the last row: the other menu's Add
        rows, others = menus(moved)
        assert rows['keys'] is False and others.get('keys', True) and others['focus'] == 0
        added = game.act(tap=['select'], ticks=2)                  # a row more: its button, and its line
        assert labels(menus(added)[0]) == ['Ana     3', 'Bruno   0', 'Davi    1']
        assert [r[0] for r in hud(added)[1]['rows']] == ['Ana', 'Bruno', 'Carla Cr']   # rows="3"
        back = game.act(tap=['up'], ticks=2)                       # up from the first: the last row
        rows, others = menus(back)
        assert others['keys'] is False and rows['items'][rows['focus']]['button'] == 'Davi    1'


def test_a_scene_seeded_by_the_state_draws_the_same_from_the_same_number(godot, project):
    with PlaySession(project, binary=godot) as game:
        game.act(ticks=2)
        for tap in (['down'], ['down'], ['down'], ['select']):     # to Next world, and into it
            game.act(tap=tap, ticks=2)
        for tap in (['down'], ['down'], ['down'], ['down']):       # the keys start on the rows again
            game.act(tap=tap, ticks=2)
        back = game.act(tap=['select'], ticks=4)                   # Back world: world 5 again
        draws = back['state']['game']['draws']
        assert back['state']['game']['world'] == 5 and len(draws) == 3
        assert draws[0] == draws[2] and draws[0] != draws[1]
        assert all(1 <= d[0] <= 6 and 1 <= d[1] <= 6 and isinstance(d[2], bool) for d in draws)


def test_the_hud_is_placed_in_its_box_and_coloured_by_the_state(godot, project, tmp_path):
    dump = tmp_path / 'probe.json'
    result = run_godot(['--path', str(project), '-s', str(PROBE), '--',
                        '--props=global_position,text,theme_override_colors/font_color', f'--out={dump}',
                        '--ticks=3'],
                       binary=godot)
    assert script_errors(result.stdout + result.stderr) == []
    nodes = json.loads(dump.read_text(encoding='utf-8'))
    hud = {k: v for k, v in nodes.items() if '/Hud' in k}
    panel = next(v for v in hud.values() if v['class'] == 'PanelContainer')
    assert panel['global_position'] == 'Vector2(10, 20)'
    texts = {json.loads(v['text']): v['theme_override_colors/font_color'] for v in hud.values()
             if v['class'] == 'Label'}
    assert texts['Pay $1,500,000 a/1/2 ===ab  |  7|abc'] == 'Color(0, 1, 0, 1)'
    assert texts[' 12'] == 'Color(1, 1, 0, 1)' and texts['  3'] == 'null'   # only when goals > 5
    assert texts['Name    '] == 'null' and 'Carla Cr' in texts               # the heading; a cut name
    assert texts['    -$2,500'] == 'Color(0.333333, 1, 0.333333, 1)'          # a column's own colour
