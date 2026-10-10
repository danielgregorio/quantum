"""scripts/export-games.py without Godot's templates: what it would export, and how."""

import importlib.util
import json
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
    assert sorted(eg.games()) == ['arena', 'chess', 'creeps', 'drift', 'hopper', 'keep', 'pong', 'robot', 'rpg', 'towers']
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
        assert f'projects/{name}/{name}.q' in page


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
