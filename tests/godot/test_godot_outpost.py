"""Outpost in Godot (PLAN_GAME_SERVER.md, Phase 4): from its title into its world.

The test is the site, as in test_godot_sign_in.py: it knows ana@site's password and signs her ticket. The game's
title has an account and a password (its box shows dots, and so does the play protocol); Enter the world signs in,
forgets the password, and goes to the mainland, where the world lets Ana in at the temple and the HUD reads her.
"""

import json
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.gameserver.session import WorldSession, serve_world
from quantum.runtime.gameserver.tickets import issue
from quantum.runtime.godot import compile_game
from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession

OUTPOST = Path(__file__).resolve().parents[2] / 'projects' / 'outpost'
SECRET = b'the outpost and its site share it'
SITE = 'https://outpost.quantumframework.net/sign-in'


class Site:
    def __init__(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
                if body.get('account') == 'ana@site' and body.get('password') == 'cheese':
                    status, answer = 200, {'ticket': issue('ana@site', 'Ana', SECRET)}
                else:
                    status, answer = 401, {'message': 'Wrong password.'}
                data = json.dumps(answer).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.http.server_port}/sign-in'
        threading.Thread(target=self.http.serve_forever, daemon=True).start()


@pytest.fixture(scope='module')
def site():
    s = Site()
    yield s
    s.http.shutdown()


@pytest.fixture(scope='module')
def outpost(godot, site, tmp_path_factory) -> Path:
    """Outpost as it is, but signing in to the test's site."""
    here = tmp_path_factory.mktemp('outpost')
    for part in ('assets', 'maps'):
        shutil.copytree(OUTPOST / part, here / part)
    shutil.copy(OUTPOST / 'outpost.server.q', here / 'outpost.server.q')
    game = (OUTPOST / 'outpost.q').read_text()
    assert SITE in game
    (here / 'outpost.q').write_text(game.replace(SITE, site.url))
    app = QuantumParser(use_cache=False).parse_file(str(here / 'outpost.q'))
    project = Path(compile_game(app, str(here / 'godot'), source_dir=str(here)))
    assert check_project(project, binary=godot) == []
    return here


def hud_texts(obs: dict) -> list:
    return [i for v in obs['screen'] if v['kind'] == 'hud' for i in v['items'] if isinstance(i, str)]


def test_from_the_title_into_the_world(outpost, godot):
    with serve_world(outpost / 'outpost.server.q', secret=SECRET) as server, \
            WorldSession(server.url, control=True) as control, \
            PlaySession(outpost / 'godot', binary=godot, world=server.url) as game:
        game.act(ticks=3)
        game.act(tap=['select'], ticks=2)                                  # the account's box
        game.act(text='ana@site\n', ticks=2)
        game.act(tap=['down'], ticks=2)
        game.act(tap=['select'], ticks=2)                                  # the password's
        typed = game.act(text='cheese\n', ticks=2)
        menu = PlaySession.screen(typed, 'menu')
        assert [i.get('value') for i in menu['items'] if 'field' in i] == ['ana@site', '******']
        game.act(tap=['down'], ticks=2)
        game.act(tap=['select'], ticks=1)                                  # Enter the world
        signed = game.until({'path': 'scene', 'op': '==', 'value': 'mainland'}, max_ticks=900)
        assert signed['scene'] == 'mainland' and signed['state']['game']['password'] == ''
        assert 'ticket' not in json.dumps(signed['state'])
        for _ in range(300):
            if 'ana@site' in control.peek()['connected']:
                break
            game.act(ticks=1)
        control.act(ticks=1)                                               # the join's tick
        seen = game.until({'path': 'world.tick', 'op': '>=', 'value': control.tick}, max_ticks=600)
        me = seen['world']['me']
        assert seen['world']['you'] == 'hero:ana@site' and me['name'] == 'Ana'
        assert 13 <= me['at']['x'] <= 17 and 20 <= me['at']['y'] <= 24     # in the temple
        texts = hud_texts(game.act(ticks=2))
        assert 'Ana   Level 1' in texts and '20 gold' in texts
