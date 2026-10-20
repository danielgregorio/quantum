"""The Hive's screen compiles from qs: tags to what hive-screen loads, and what the compiler refuses.

A `q:application type="screen"` is what the Hive shows on the machine's
screen: sheets, a scene of sprites and text, and per event what happens
in it. quantum/runtime/screen reads it against its schema and writes
screen.toml, the font sheet and the sprite sheets. A promise the file
cannot keep is refused with the line: a sheet that is not there, a frame
it lacks, a {field} the event lacks, a target no sprite is named.
"""

import tomllib
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.screen import ScreenCompileError, compile_screen, read_screen
from quantum.runtime.screen import font, png
from quantum.runtime.screen.schema import ACTIONS, EVENTS, TAGS

REPO = Path(__file__).resolve().parents[2]

GOOD = '''<q:application id="x" type="screen">
  <qs:sheet name="cell" src="art/cells.png" tile="8">
    <qs:animation name="smoke" frames="1,2,3" fps="6" loop="false" />
    <qs:animation name="glow" frames="0,1" />
  </qs:sheet>
  <qs:particles name="puff" preset="puff" color="#fff" amount="6" />
  <qs:scene width="128" height="96" background="#102030">
    <qs:text value="Café, Hive" x="4" y="4" align="left" />
    <qs:sprite name="nginx" sheet="cell" frame="0" x="10" y="20" />
    <qs:sprite name="redis-server" sheet="cell" x="30" y="20" animation="glow" hidden="true" />
    <qs:emitter particles="puff" x="60" y="60" />
    <qs:offers x="4" y="40" width="120" rows="3" title="Offers" />
    <qs:notices x="4" y="80" width="120" rows="1" />
    <qs:bar side="top" title="Quantum OS" left="{host}" right="{cores} cores · {level} · {clock}" />
    <qs:bar side="bottom" right="{offers} offers" color="#c0c0c0" />
  </qs:scene>
  <qs:on event="service-crash">
    <qs:animate target="{service}" name="smoke" />
    <qs:emit particles="puff" at="{service}" dx="4" dy="4" />
    <qs:tween target="nginx" property="y" to="30" seconds="0.5" trans="bounce" ease="out" />
    <qs:show target="redis-server" />
    <qs:say text="{service} stopped (exit {exit_code}): {title}" seconds="3" />
  </qs:on>
  <qs:on event="done">
    <qs:frame target="nginx" frame="0" />
  </qs:on>
</q:application>'''


def sheet(tmp_path: Path, frames: int = 4, name: str = 'art/cells.png', size: int = 8) -> Path:
    """A PNG of `frames` solid frames of size x size, in a row."""
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    colours = [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255), (255, 255, 0, 255), (0, 0, 0, 0)]
    rows = [b''.join(bytes(colours[i % len(colours)]) * size for i in range(frames)) for _ in range(size)]
    png.write(path, size * frames, size, rows)
    return path


def parse(text: str, tmp_path: Path, name: str = 'screen.q'):
    source = tmp_path / name
    source.write_text(text, encoding='utf-8')
    return QuantumParser(use_cache=False).parse_file(str(source))


def wrapped(body: str, scene: str = '') -> str:
    return (f'<q:application id="x" type="screen">\n<qs:sheet name="cell" src="art/cells.png" tile="8">'
            f'<qs:animation name="smoke" frames="1,2" /></qs:sheet>\n<qs:particles name="puff" preset="puff" />\n'
            f'<qs:scene width="128" height="96"><qs:sprite name="nginx" sheet="cell" x="1" y="1" />{scene}</qs:scene>\n'
            f'{body}\n</q:application>')


def test_a_screen_compiles_to_the_scene_the_font_and_the_sheets(tmp_path):
    sheet(tmp_path)
    written = compile_screen(parse(GOOD, tmp_path), str(tmp_path / 'out'))
    assert sorted(written) == ['art/cells.png', 'font.png', 'screen.toml']
    scene = tomllib.loads(Path(written['screen.toml']).read_text(encoding='utf-8'))

    assert scene['meta'] == {'version': 1}
    assert scene['scene'] == {'width': 128, 'height': 96, 'background': '#102030'}
    assert scene['font'] == {'src': 'font.png', 'cell': [6, 10]}
    cell, = scene['sheets']
    assert (cell['name'], cell['src'], cell['tile'], cell['frames']) == ('cell', 'art/cells.png', [8, 8], 4)
    assert cell['animations'] == [{'name': 'smoke', 'frames': [1, 2, 3], 'fps': 6.0, 'loop': False},
                                  {'name': 'glow', 'frames': [0, 1], 'fps': 8.0, 'loop': True}]
    assert scene['particles'] == [{'name': 'puff', 'preset': 'puff', 'color': '#ffffff', 'amount': 6}]
    kinds = [n['kind'] for n in scene['nodes']]
    assert kinds == ['text', 'sprite', 'sprite', 'emitter', 'offers', 'notices', 'bar', 'bar']
    redis = scene['nodes'][2]
    assert redis == {'kind': 'sprite', 'name': 'redis-server', 'sheet': 'cell', 'frame': 0, 'x': 30, 'y': 20,
                     'animation': 'glow', 'hidden': True}
    assert scene['nodes'][4]['focus'] == '#ffd34d'
    assert scene['nodes'][4]['title'] == 'Offers'
    assert 'title' not in scene['nodes'][5], 'a panel with no title is written without one'
    assert scene['nodes'][6] == {'kind': 'bar', 'side': 'top', 'title': 'Quantum OS', 'left': '{host}',
                                 'right': '{cores} cores · {level} · {clock}', 'color': '#8a8aa0',
                                 'accent': '#ffd34d'}
    assert scene['nodes'][7] == {'kind': 'bar', 'side': 'bottom', 'right': '{offers} offers', 'color': '#c0c0c0',
                                 'accent': '#ffd34d'}
    crash, done = scene['rules']
    assert crash['event'] == 'service-crash'
    assert [a['kind'] for a in crash['actions']] == ['animate', 'emit', 'tween', 'show', 'say']
    assert crash['actions'][2] == {'kind': 'tween', 'target': 'nginx', 'property': 'y', 'to': 30.0, 'seconds': 0.5,
                                   'trans': 'bounce', 'ease': 'out', 'repeat': 0, 'yoyo': False}
    assert crash['actions'][4]['text'] == '{service} stopped (exit {exit_code}): {title}'
    assert done['actions'] == [{'kind': 'frame', 'target': 'nginx', 'frame': 0}]
    # the sheets travel with the scene, the font is drawn
    assert png.size_of(Path(written['art/cells.png'])) == (32, 8)
    width, height, _ = font.render()
    assert png.size_of(Path(written['font.png'])) == (width, height)


def test_the_sheets_are_not_copied_onto_themselves(tmp_path):
    sheet(tmp_path)
    written = compile_screen(parse(GOOD, tmp_path), str(tmp_path))
    assert Path(written['art/cells.png']) == tmp_path / 'art' / 'cells.png'


def test_the_model_resolves_a_sheet_s_frames_from_the_png(tmp_path):
    sheet(tmp_path, frames=6)
    screen = read_screen(parse(GOOD, tmp_path))
    assert screen.sheets['cell'].frames == 6
    assert screen.sprite('nginx').attrs['frame'] == 0
    assert screen.sprite('nobody') is None


def test_a_3_digit_colour_is_widened(tmp_path):
    sheet(tmp_path)
    screen = read_screen(parse(wrapped('', scene='<qs:text value="hi" x="0" y="0" color="#1aF" />'), tmp_path))
    assert screen.nodes[-1].attrs['color'] == '#11aaff'


REFUSED = [
    # the scene
    ('<qs:on event="done"><qs:say text="x" /></qs:on>', 'a screen needs a <qs:scene>',
     lambda tmp: '<q:application id="x" type="screen"><qs:on event="done"><qs:say text="x" /></qs:on></q:application>'),
    ('two scenes', 'one <qs:scene> per screen',
     lambda tmp: wrapped('<qs:scene width="100" height="100" />')),
    ('a sheet that is not there', 'no such file next to the .q',
     lambda tmp: '<q:application id="x" type="screen"><qs:sheet name="c" src="art/none.png" tile="8" />'
                 '<qs:scene /></q:application>'),
    ('a sheet that is not a PNG', 'is not a PNG',
     lambda tmp: ((tmp / 'art').mkdir(exist_ok=True), (tmp / 'art' / 'bad.png').write_bytes(b'nope' * 20),
                  '<q:application id="x" type="screen"><qs:sheet name="c" src="art/bad.png" tile="8" />'
                  '<qs:scene /></q:application>')[-1]),
    ('a sheet outside the folder', 'next to the .q or in a folder below it',
     lambda tmp: '<q:application id="x" type="screen"><qs:sheet name="c" src="../cells.png" tile="8" />'
                 '<qs:scene /></q:application>'),
    ('a tile the sheet is not a whole number of', 'not a whole number of 5x5 frames',
     lambda tmp: '<q:application id="x" type="screen"><qs:sheet name="c" src="art/cells.png" tile="5" />'
                 '<qs:scene /></q:application>'),
    ('an animation of a frame the sheet lacks', 'uses frame 9; sheet cell has 4',
     lambda tmp: '<q:application id="x" type="screen"><qs:sheet name="cell" src="art/cells.png" tile="8">'
                 '<qs:animation name="a" frames="0,9" /></qs:sheet><qs:scene /></q:application>'),
    ('a sprite of no sheet', 'no <qs:sheet> of that name',
     lambda tmp: wrapped('', scene='<qs:sprite sheet="ghost" x="0" y="0" />')),
    ('a sprite of a frame the sheet lacks', 'sheet cell has 4 frames',
     lambda tmp: wrapped('', scene='<qs:sprite sheet="cell" frame="4" x="0" y="0" />')),
    ('a sprite of an animation the sheet lacks', 'has no animation of that name',
     lambda tmp: wrapped('', scene='<qs:sprite sheet="cell" animation="run" x="0" y="0" />')),
    ('two sprites of one name', 'two <qs:sprite name="nginx">',
     lambda tmp: wrapped('', scene='<qs:sprite name="nginx" sheet="cell" x="0" y="0" />')),
    ('a field in the scene', 'goes in a <qs:on>, not in the scene',
     lambda tmp: wrapped('', scene='<qs:text value="{title}" x="0" y="0" />')),
    ('two offers', 'one <qs:offers> per screen',
     lambda tmp: wrapped('', scene='<qs:offers x="0" y="0" width="100" /><qs:offers x="0" y="0" width="100" />')),
    ('a field in a panel\'s title', '<qs:notices> title= holds {title}: a {field} is filled in from an event',
     lambda tmp: wrapped('', scene='<qs:notices x="0" y="0" width="100" title="{title}" />')),
    ('two bars on one side', 'one <qs:bar side="top"> per screen',
     lambda tmp: wrapped('', scene='<qs:bar side="top" /><qs:bar side="top" title="x" />')),
    ('a bar on no side', '<qs:bar> side="left" is not one of: top, bottom',
     lambda tmp: wrapped('', scene='<qs:bar side="left" />')),
    ('an event\'s field in a bar', '<qs:bar> right= holds {service}: a bar shows the screen\'s own fields '
     '({clock}, {level}, {cores}, {host}, {offers})',
     lambda tmp: wrapped('', scene='<qs:bar side="bottom" right="{service}" />')),
    ('an emitter of no particles', 'no <qs:particles> of that name',
     lambda tmp: wrapped('', scene='<qs:emitter particles="rain" x="0" y="0" />')),
    ('an emitter of a level there is not', '<qs:emitter> level= is 1 (with the effects) or 2',
     lambda tmp: wrapped('', scene='<qs:emitter particles="puff" x="0" y="0" level="3" />')),
    # the rules
    ('a field the event lacks', 'not a field of service-crash (it has: unit, service, exit_code, title, body, severity)',
     lambda tmp: wrapped('<qs:on event="service-crash"><qs:say text="{svc}" /></qs:on>')),
    ('a target no sprite is named', 'no <qs:sprite name="apache"> in the scene (named sprites: nginx)',
     lambda tmp: wrapped('<qs:on event="done"><qs:frame target="apache" frame="0" /></qs:on>')),
    ('an animation the target\'s sheet lacks', 'sheet cell of sprite nginx has no animation of that name',
     lambda tmp: wrapped('<qs:on event="done"><qs:animate target="nginx" name="run" /></qs:on>')),
    ('an animation no sheet has, on a field', 'no sheet has an animation of that name',
     lambda tmp: wrapped('<qs:on event="service-crash"><qs:animate target="{service}" name="run" /></qs:on>')),
    ('a frame the target\'s sheet lacks', 'sheet cell has 4 frames',
     lambda tmp: wrapped('<qs:on event="done"><qs:frame target="nginx" frame="7" /></qs:on>')),
    ('an emit of no particles', 'no <qs:particles> of that name',
     lambda tmp: wrapped('<qs:on event="done"><qs:emit particles="rain" at="nginx" /></qs:on>')),
    ('a rule that does nothing', 'does nothing: give it an action, or leave it out',
     lambda tmp: wrapped('<qs:on event="done" />')),
    ('two rules on one event', 'two <qs:on event="done">',
     lambda tmp: wrapped('<qs:on event="done"><qs:say text="a" /></qs:on><qs:on event="done"><qs:say text="b" /></qs:on>')),
    ('an event that is not one', 'event="reboot" is not one of',
     lambda tmp: wrapped('<qs:on event="reboot"><qs:say text="a" /></qs:on>')),
    ('a tween of no time', 'seconds= is more than 0',
     lambda tmp: wrapped('<qs:on event="done"><qs:tween target="nginx" property="x" to="1" seconds="0" /></qs:on>')),
    ('a tween of a property that is not one', 'property="rotation" is not one of: x, y, scale, alpha',
     lambda tmp: wrapped('<qs:on event="done"><qs:tween target="nginx" property="rotation" to="1" /></qs:on>')),
    # the language
    ('an unknown tag', '<qs:button> is not a screen tag',
     lambda tmp: wrapped('<qs:button label="x" />')),
    ('an unknown attribute', "has no attribute 'speed'",
     lambda tmp: wrapped('<qs:on event="done"><qs:say text="a" speed="1" /></qs:on>')),
    ('a scene tag at the top', '<qs:sprite> goes inside <qs:scene>',
     lambda tmp: wrapped('<qs:sprite sheet="cell" x="0" y="0" />')),
    ('an action at the top', '<qs:say> goes inside <qs:on>',
     lambda tmp: wrapped('<qs:say text="x" />')),
    ('a statement', '<q:set> is not part of the screen language',
     lambda tmp: wrapped('<q:set name="n" value="1" />')),
    ('text where a tag goes', 'declarations, not script',
     lambda tmp: wrapped('<qs:on event="done">print(1)<qs:say text="x" /></qs:on>')),
    ('a number that is not one', 'x= is a whole number, not',
     lambda tmp: wrapped('', scene='<qs:text value="x" x="ten" y="0" />')),
    ('a colour that is not one', 'is a colour, #rgb or #rrggbb, not',
     lambda tmp: wrapped('', scene='<qs:text value="x" x="0" y="0" color="red" />')),
]


@pytest.mark.parametrize('case', REFUSED, ids=[c[0][:40] for c in REFUSED])
def test_what_the_compiler_refuses(case, tmp_path):
    _, message, source = case
    sheet(tmp_path)
    with pytest.raises(ScreenCompileError) as e:
        compile_screen(parse(source(tmp_path), tmp_path), str(tmp_path / 'out'))
    assert message in str(e.value), str(e.value)
    assert e.value.line is not None or 'needs a <qs:scene>' in message


def test_the_error_names_the_file_and_the_line(tmp_path):
    sheet(tmp_path)
    with pytest.raises(ScreenCompileError) as e:
        read_screen(parse(wrapped('<qs:on event="done"><qs:frame target="apache" frame="0" /></qs:on>'), tmp_path))
    assert str(e.value).startswith(str(tmp_path / 'screen.q') + ':5:')


# ---------------------------------------------------------------- the schema and the font

def test_every_event_has_the_common_fields_and_the_hive_s_own():
    from quantum.runtime.hive.schema import EVENTS as HIVE
    for name, event in HIVE.items():
        assert set(EVENTS[name].fields) == set(event.fields) | {'title', 'body', 'severity'}
    assert set(EVENTS['offer'].fields) == {'count', 'title', 'body', 'severity'}
    assert set(EVENTS['done'].fields) == {'action', 'service', 'package', 'output'}
    assert set(EVENTS['failed'].fields) == set(EVENTS['done'].fields)


def test_every_action_is_a_tag_inside_on_and_every_node_a_tag_inside_scene():
    for action in ACTIONS:
        assert TAGS[action].parents == ('on',)
    for node in ('sprite', 'text', 'emitter', 'offers', 'notices', 'bar'):
        assert TAGS[node].parents == ('scene',)


def test_the_font_has_every_printable_ascii_and_latin1_letter_of_portuguese():
    for ch in 'abcxyzABCXYZ0189 !?.,;:-_()[]{}<>/\\@#$%&*+=\'"`~^|':
        assert font.rows_of(ch) != font.rows_of('\u0080'), ch          # not the box
    for ch in 'áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇñÑ':
        assert font.rows_of(ch) != font.rows_of('\u0080'), ch
    assert font.cell_index(ord('A')) == 33
    assert font.cell_index(ord('á')) == 95 + (0xE1 - 0xA0)
    assert font.cell_index(0x2603) is None
    width, height, rows = font.render()
    assert (width, height) == (32 * 6, 6 * 10)
    assert len(rows) == height and all(len(r) == width * 4 for r in rows)


def test_an_accent_sits_above_its_letter():
    a, a_acute = font.rows_of('a'), font.rows_of('á')
    assert a[4:] == a_acute[4:]                       # the same letter
    assert any('#' in r for r in a_acute[2:4])        # with a mark above it
    assert not any('#' in r for r in a[:4])
