"""scripts/export-games.py without Godot's templates: what it would export, and how."""

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load():
    spec = importlib.util.spec_from_file_location('export_games', REPO / 'scripts' / 'export-games.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_project_is_a_game_to_export():
    eg = load()
    assert sorted(eg.games()) == ['arena', 'chess', 'creeps', 'drift', 'hopper', 'keep', 'pong', 'robot', 'towers']
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
