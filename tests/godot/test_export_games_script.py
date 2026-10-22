"""scripts/export-games.py without Godot's templates: what it would export, and how."""

import html
import importlib.util
import json
import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load():
    spec = importlib.util.spec_from_file_location('export_games', REPO / 'scripts' / 'export-games.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_project_is_a_game_to_export():
    eg = load()
    assert sorted(eg.games()) == ['arena', 'bricks', 'chess', 'crates', 'creeps', 'delve', 'drift', 'hopper', 'keep', 'pong',
                                  'rally', 'robot', 'rpg', 'siege', 'towers']
    assert eg.games()['pong'] == REPO / 'projects' / 'pong' / 'pong.q'


def test_the_web_preset_runs_without_threads_and_the_desktop_ones_embed_the_pack():
    eg = load()
    web = eg.preset_file('pong', 'Web', Path('/out/index.html'))
    assert 'platform="Web"' in web and 'variant/thread_support=false' in web and 'export_path="/out/index.html"' in web
    assert 'include_filter=""' in web
    assert 'platform="Linux"' in eg.preset_file('pong', 'Linux', Path('/o/pong.x86_64'))
    assert 'platform="Windows Desktop"' in eg.preset_file('pong', 'Windows', Path('/o/pong.exe'))
    assert 'binary_format/embed_pck=true' in eg.preset_file('pong', 'Linux', Path('/o/pong.x86_64'))


def test_the_play_page_links_every_game(tmp_path):
    page = (REPO / 'docs' / 'targets' / 'play.md').read_text(encoding='utf-8')
    for name in load().games():
        assert f'https://quantumframework.net/games/{name}/' in page
        assert f'{name}-linux.zip' in page and f'{name}-windows.zip' in page
        assert f'https://quantumframework.net/games/{name}/source/' in page


def test_the_games_page_shows_every_game_with_its_screenshot_and_links(tmp_path):
    eg = load()
    meta = json.loads((REPO / 'projects' / 'games.json').read_text(encoding='utf-8'))['games']
    assert sorted(g['name'] for g in meta) == sorted(eg.games())          # every game, once
    for g in meta:
        assert (REPO / 'projects' / g['name'] / 'screenshot.png').is_file()
        assert g['title'] and g['blurb'] and g['controls'] and g['players']
    # as an export leaves them: a web build and the two zips for each game but towers' windows zip
    for name in eg.games():
        (tmp_path / name).mkdir()
        (tmp_path / name / 'index.html').write_text('x')
        (tmp_path / name / f'{name}-linux.zip').write_text('x')
        if name != 'towers':
            (tmp_path / name / f'{name}-windows.zip').write_text('x')
    page = eg.write_index(tmp_path).read_text(encoding='utf-8')
    order = [page.index(f'id="{g["name"]}"') for g in meta]
    assert order == sorted(order)                                          # in the order of games.json
    for name in eg.games():
        assert f'href="{name}/">Play in the browser' in page and f'src="{name}/screenshot.png"' in page
        assert (tmp_path / name / 'screenshot.png').is_file()
        assert f'href="{name}/{name}-linux.zip"' in page
    assert 'towers-windows.zip' not in page and 'href="chess/chess-windows.zip"' in page
    # a game that was not built is not on the page
    shutil.rmtree(tmp_path / 'pong')
    assert 'id="pong"' not in eg.write_index(tmp_path).read_text(encoding='utf-8')


def test_each_game_has_a_page_of_its_source(tmp_path):
    eg = load()
    for name in eg.games():
        (tmp_path / name).mkdir()
        (tmp_path / name / 'index.html').write_text('x')
    index = eg.write_index(tmp_path).read_text(encoding='utf-8')
    reference = (REPO / 'docs' / 'targets' / 'games.md').read_text(encoding='utf-8')
    anchors = {'statements', 'gd-attributes'} | {f'qg-{t}' for t in re.findall(r'^### `qg:([a-z-]+)`', reference, re.M)}
    for name, q in eg.games().items():
        assert f'href="{name}/source/">View the source' in index
        page = (tmp_path / name / 'source' / 'index.html').read_text(encoding='utf-8')
        text = q.read_text(encoding='utf-8')
        assert (tmp_path / name / 'source' / f'{name}.q').read_text(encoding='utf-8') == text   # to download
        lines = text.count('\n') + (not text.endswith('\n'))
        assert f'id="L{lines}"' in page and f'id="L{lines + 1}"' not in page                    # every line
        assert '<qg:' not in page and '<q:' not in page                                        # escaped
        assert 'href="../">Play in the browser' in page
        # every tag links to an entry of the reference, and every tooltip has its text
        links = set(re.findall(r'href="\.\./\.\./\.\./targets/games\.html#([\w-]+)"', page))
        assert links and links <= anchors, links - anchors
        docs = json.loads(re.search(r'const DOCS = (\{.*?\});\n', page).group(1))
        assert set(re.findall(r'data-t="([^"]+)"', page)) == set(docs) and all(docs.values())
    # a game's other sources (a level drawn in Tiled) are on its page too, a tab each
    hopper = (tmp_path / 'hopper' / 'source' / 'index.html').read_text(encoding='utf-8')
    assert [p.name for p in eg.source_files('hopper')] == ['hopper.q', 'level-2.tmx']
    assert 'id="levels-level-2-tmx-L1"' in hopper and '<button type="button">levels/level-2.tmx</button>' in hopper
    assert (tmp_path / 'hopper' / 'source' / 'levels' / 'level-2.tmx').is_file()
    assert '<button type="button">' not in (tmp_path / 'pong' / 'source' / 'index.html').read_text(encoding='utf-8')


def test_the_highlighted_source_is_the_source():
    eg = load()
    for name in eg.games():
        for path in eg.source_files(name):
            text = path.read_text(encoding='utf-8')
            lines = [html.unescape(re.sub(r'<[^>]+>', '', line)) for line in eg.highlight(text, {})]
            assert '\n'.join(lines) + '\n' * text.endswith('\n') == text, path
    docs = {}
    line, statement = eg.highlight('<qg:character id="p" controller="platformer" x="{w / 2}"/> <!-- a < b -->\n'
                                   '<q:set name="a" value="1" />\n', docs)
    assert line.startswith('<span class="b">&lt;</span><a class="t" href="../../../targets/games.html#qg-character" '
                           'data-t="character">qg:character</a>')
    assert '<span class="a" data-t="character controller">controller</span>=<span class="v">"platformer"</span>' in line
    assert '<span class="v">"</span><span class="e">{w / 2}</span><span class="v">"</span>' in line
    assert '<span class="c">&lt;!-- a &lt; b --&gt;</span>' in line
    assert '<a class="k" href="../../../targets/games.html#statements">q:set</a>' in statement
    assert set(docs) == {'character', 'character controller'} and docs['character'].startswith('A body the player')

def test_what_the_browser_check_expects_is_in_each_game(tmp_path):
    # scripts/check-games-in-browser.py waits for these scenes and actions in
    # the web build; a scene renamed in a .q must be renamed here too.
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    for g in json.loads((REPO / 'projects' / 'games.json').read_text(encoding='utf-8'))['games']:
        src = REPO / 'projects' / g['name']
        out = compile_game(QuantumParser(use_cache=False).parse_file(str(src / f'{g["name"]}.q')),
                           str(tmp_path / g['name']), source_dir=str(src))
        game = json.loads((Path(out) / 'game.json').read_text(encoding='utf-8'))
        check = g['check']
        assert check['scene'] == game['initial'], g['name']
        assert check['press'] and ('then' in check or check.get('actions')), g['name']
        if 'then' in check:
            assert check['then'] in game['scenes'], g['name']
        for action in check.get('actions', []):
            assert action in game['actions'], (g['name'], action)


def test_with_a_relay_each_networked_game_can_be_played_online(tmp_path, monkeypatch):
    eg = load()
    for name in eg.games():
        (tmp_path / name).mkdir()
        (tmp_path / name / 'index.html').write_text('x')
    monkeypatch.delenv('QUANTUM_RELAY_URL', raising=False)
    assert 'class="online"' not in eg.write_index(tmp_path).read_text(encoding='utf-8')   # no relay: no button
    monkeypatch.setenv('QUANTUM_RELAY_URL', 'wss://relay.example/')
    page = eg.write_index(tmp_path).read_text(encoding='utf-8')
    online = {name for name in eg.games() if f'data-game="{name}" data-relay="wss://relay.example"' in page}
    assert online == {'arena', 'bricks', 'chess', 'delve', 'pong', 'rally', 'siege', 'towers'}   # with qg:multiplayer
