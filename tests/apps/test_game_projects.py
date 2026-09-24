"""The game projects build, and what they serve is what they build (Laboratory).

projects/quantum-snake, quantum-tictactoe and kenney-platformer
are a page that frames (or redirects to) an HTML game in static/, built by
`quantum run <game>.q` from the .q next to it. Nothing checked them: the
committed builds were months older than their sources. This builds each game,
checks its JavaScript with Node (as tests/test_game_e2e.py does for examples/),
serves the project and asks for the page and the game it points to — and, for
the games whose build is committed as it comes out of the builder, checks the
committed file IS the build, so a change to the source or to the codegen that
is not rebuilt shows here.

The file name starts with test_game_, so the root conftest marks it
`laboratory`: it runs in the Laboratory CI job.
"""

import logging
import re
import shutil
from pathlib import Path

import pytest

from tests.test_game_e2e import validate_balanced, validate_js_syntax

PROJECTS = Path(__file__).resolve().parents[2] / 'projects'

# project, game source, the build the page serves, the build is kept in sync
GAMES = [
    ('quantum-snake', 'snake.q', 'static/game.html', True),
    ('quantum-tictactoe', 'tictactoe.q', 'static/game.html', True),
    ('kenney-platformer', 'kenney_platformer.q', 'static/index.html', True),
]


def build(project, source):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.game_builder import GameBuilder
    return GameBuilder().build(QuantumParser().parse_file(str(PROJECTS / project / source)))


@pytest.mark.parametrize('project,source,served,synced', GAMES, ids=[g[0] for g in GAMES])
def test_the_game_builds_to_valid_javascript(project, source, served, synced):
    html = build(project, source)
    assert not validate_balanced(html)
    ok, error = validate_js_syntax(html)
    assert ok, error


@pytest.mark.parametrize('project,source,served,synced', GAMES, ids=[g[0] for g in GAMES])
def test_the_committed_build_is_valid_and_current(project, source, served, synced):
    committed = (PROJECTS / project / served).read_text(encoding='utf-8')
    ok, error = validate_js_syntax(committed)
    assert ok, error
    if synced:
        assert committed.replace('\r\n', '\n') == build(project, source), (
            f'projects/{project}/{served} is not the build of {source}: rebuild it with '
            f'`quantum run {source}` and copy the output to {served}')


@pytest.mark.parametrize('project,source,served,synced', GAMES, ids=[g[0] for g in GAMES])
def test_the_page_serves_the_game(project, source, served, synced, tmp_path, monkeypatch):
    app = tmp_path / project
    shutil.copytree(PROJECTS / project, app)
    monkeypatch.chdir(app)
    from quantum.runtime.web_server import QuantumWebServer
    logging.disable(logging.WARNING)
    try:
        client = QuantumWebServer(str(app / 'quantum.config.yaml')).app.test_client()
        page = client.get('/')
        assert page.status_code == 200
        target = re.search(r'(?:src|url)=/?(static/[\w.-]+\.html)', page.get_data(as_text=True).replace('"', ''))
        assert target and target.group(1) == served
        assert client.get('/' + served).status_code == 200
    finally:
        logging.disable(logging.NOTSET)
