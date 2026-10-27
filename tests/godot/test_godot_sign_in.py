"""qg:sign-in in Godot (PLAN_GAME_SERVER.md, Phase 4): a game signs in to a site, and comes into its world.

The test is the site: an HTTP server that knows ana@site's password and answers a ticket signed with the secret
the world has. A wrong password is the site's refusal, heard by qg:on-fail. The right one is a ticket the game
keeps (not in its state, nor in a save) and comes into the world with, as the scene of the world is entered: the
world lets it in as ana@site, the hero showing the name the site said.
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

DEN = Path(__file__).resolve().parents[1] / 'gameserver' / 'worlds' / 'den'
SECRET = b'the site and its world share it'

DOOR = '''<q:application id="door" type="game">
  <qg:connect world="den.server.q" />
  <qg:tileset name="land" src="den.png" tile="16" />
  <qg:spritesheet name="folk" src="folk.png" tile="16" />
  <qg:spritesheet name="beasts" src="rat.png" tile="16" />
  <qg:prefab name="Hero" sheet="folk" frame="0" hitbox="12x14" />
  <qg:prefab name="Rat" sheet="beasts" frame="0" hitbox="12x10" />
  <q:set name="note" value="" />

  <qg:scene name="door" width="320" height="180">
    <qg:menu>
      <qg:button label="Sign in">
        <qg:sign-in to="SITE" data="{ {'account': 'ana@site', 'password': 'cheese'} }" timeout="10">
          <qg:on-done>
            <q:set name="note" value="{'Hello, ' + reply.name}" />
            <qg:goto-scene name="den" />
          </qg:on-done>
          <qg:on-fail><q:set name="note" value="{reason}" /></qg:on-fail>
        </qg:sign-in>
      </qg:button>
      <qg:button label="A wrong password">
        <qg:sign-in to="SITE" data="{ {'account': 'ana@site', 'password': 'rat'} }" timeout="10">
          <qg:on-fail><q:set name="note" value="{reason}" /></qg:on-fail>
        </qg:sign-in>
      </qg:button>
    </qg:menu>
  </qg:scene>

  <qg:scene name="den" width="320" height="180" world="true">
    <qg:tilemap tileset="land" src="den.tmx" />
    <qg:mirror view="around" />
  </qg:scene>
</q:application>
'''


class Site:
    """The site's sign-in: ana@site's password is cheese."""

    def __init__(self):
        outer = self
        self.received = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
                outer.received.append(body)
                if body.get('account') == 'ana@site' and body.get('password') == 'cheese':
                    status, answer = 200, {'ticket': issue('ana@site', 'Ana', SECRET), 'name': 'Ana'}
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
def door(godot, site, tmp_path_factory) -> Path:
    """The den of a site's accounts, and the game that signs in to it."""
    here = tmp_path_factory.mktemp('door')
    for name in ('den.tmx', 'den.png', 'folk.png', 'rat.png'):
        shutil.copy(DEN / name, here / name)
    world = (DEN / 'den.server.q').read_text().replace('<q:gameserver name="den"',
                                                       '<q:gameserver name="den" accounts="site"')
    (here / 'den.server.q').write_text(world.replace('per-player="true"', 'per-player="true" persist="true"'))
    (here / 'door.q').write_text(DOOR.replace('SITE', site.url))
    app = QuantumParser(use_cache=False).parse_file(str(here / 'door.q'))
    project = Path(compile_game(app, str(here / 'godot'), source_dir=str(here)))
    assert check_project(project, binary=godot) == []
    return here


def test_a_wrong_password_is_refused_and_the_right_one_comes_into_the_world(door, site, godot):
    with serve_world(door / 'den.server.q', secret=SECRET) as server, \
            WorldSession(server.url, control=True) as control, \
            PlaySession(door / 'godot', binary=godot, world=server.url) as game:
        game.act(ticks=3)
        game.act(tap=['down'], ticks=2)
        game.act(tap=['select'], ticks=1)                                  # "A wrong password"
        refused = game.until({'path': 'state.game.note', 'op': '!=', 'value': ''}, max_ticks=900)
        assert refused['state']['game']['note'] == '401: Wrong password.' and refused['scene'] == 'door'
        assert site.received[-1] == {'account': 'ana@site', 'password': 'rat'}
        game.act(tap=['up'], ticks=2)
        game.act(tap=['select'], ticks=1)                                  # "Sign in"
        signed = game.until({'path': 'scene', 'op': '==', 'value': 'den'}, max_ticks=900)
        assert signed['state']['game']['note'] == 'Hello, Ana'
        assert any(e['kind'] == 'signed-in' for e in signed['events'])
        assert 'ticket' not in json.dumps(signed['state'])                 # the game's, not its state's
        for _ in range(300):
            if 'ana@site' in control.peek()['connected']:
                break
            game.act(ticks=1)
        control.act(ticks=1)                                               # the join's tick
        seen = game.until({'path': 'world.tick', 'op': '>=', 'value': control.tick}, max_ticks=600)
        assert seen['world']['you'] == 'hero:ana@site' and seen['world']['me']['name'] == 'Ana'
        assert control.peek()['players'] == {'ana@site': 'hero:ana@site'}
