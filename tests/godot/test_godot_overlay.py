"""qg:overlay and qg:post in Godot: a beta's report, from any screen, to a server of the test.

An overlay opens over whatever scene is shown, from a button (qg:open-overlay) or from its action in any scene
(the [!] of a qg:touch-button, F9); the scene under it stands still and the play protocol sees the overlay, with
the scene it is over. scene_name() and focused() there say where the player was: the scene, and the option the
cursor was on. qg:post sends the report as JSON to a real HTTP server the test starts, and its answer runs
qg:on-done (`reply`) or qg:on-fail (`reason`). save_text() is the game as a qg:save writes it.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.godot import compile_game
from quantum.runtime.godot.errors import GameCompileError
from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession

BETA = '''<q:application id="beta" type="game">
  <q:set name="server" value="SERVER" type="string" />
  <q:set name="ticks_title" value="0" type="number" />
  <q:set name="reports" value="0" type="number" />
  <qg:input action="report" keys="F9" />
  <qg:touch-button action="report" x="308" y="12" size="16" label="!" show="always" />

  <qg:overlay name="report" action="report" shade="0.5">
    <q:set name="seen" value="{scene_name()}" type="string" />
    <q:set name="option" value="{focused()}" type="string" />
    <q:set name="status" value="" type="string" />
    <qg:hud position="top-left">
      <qg:text value="{'Report from ' + seen + ' (' + option + ')'}" />
      <qg:text bind="status" />
    </qg:hud>
    <qg:menu>
      <qg:button label="Send">
        <q:set name="status" value="Sending" />
        <qg:post to="{server}" data="{ {'scene': seen, 'option': option, 'save': save_text()} }" timeout="5">
          <qg:on-done>
            <q:set name="status" value="{'Report no. ' + str(reply.number) + ' sent'}" />
            <q:set name="reports" value="{reports + 1}" />
          </qg:on-done>
          <qg:on-fail><q:set name="status" value="{'Kept: ' + reason}" /></qg:on-fail>
        </qg:post>
      </qg:button>
      <qg:button label="To the pitch"><qg:goto-scene name="pitch" /></qg:button>
      <qg:button label="Back"><qg:close-overlay /></qg:button>
    </qg:menu>
  </qg:overlay>

  <qg:scene name="title" width="320" height="180">
    <qg:timer every="1"><q:set name="ticks_title" value="{ticks_title + 1}" /></qg:timer>
    <qg:menu>
      <qg:button label="Play"><qg:goto-scene name="pitch" /></qg:button>
      <qg:button label="Options" />
      <qg:button label="Report a bug"><qg:open-overlay name="report" /></qg:button>
    </qg:menu>
  </qg:scene>

  <qg:scene name="pitch" width="320" height="180">
    <qg:hud><qg:text value="'The pitch'" /></qg:hud>
  </qg:scene>
</q:application>
'''


class Server:
    """An HTTP server of the test: keeps each JSON body posted to it and answers with `answer`."""

    def __init__(self):
        self.received = []
        self.answer = (201, {'number': 7})
        self.delay = 0.0          # seconds before it answers
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get('Content-Length', 0))
                outer.received.append((self.path, self.headers.get('Content-Type'),
                                       json.loads(self.rfile.read(length))))
                time.sleep(outer.delay)
                status, body = outer.answer
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.http.server_port}/api/reports'
        threading.Thread(target=self.http.serve_forever, daemon=True).start()

    def close(self):
        self.http.shutdown()


def build(tmp_path: Path, source: str) -> Path:
    src = tmp_path / 'game.q'
    src.write_text(source, encoding='utf-8')
    return Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(tmp_path / 'godot'),
                             source_dir=str(tmp_path)))


@pytest.fixture(scope='module')
def server():
    s = Server()
    yield s
    s.close()


@pytest.fixture(scope='module')
def beta(godot, server, tmp_path_factory) -> Path:
    out = build(tmp_path_factory.mktemp('beta'), BETA.replace('SERVER', server.url))
    assert check_project(out, binary=godot) == []
    return out


def items(obs: dict) -> list:
    return [i['button'] for i in PlaySession.screen(obs, 'menu')['items']]


def hud(obs: dict) -> list:
    return PlaySession.screen(obs, 'hud')['items']


def test_the_overlay_opens_over_the_scene_which_stands_still(beta, godot, server):
    server.answer = (201, {'number': 7})
    with PlaySession(beta, binary=godot) as game:
        game.act(ticks=3)
        game.act(tap=['down'], ticks=2)
        game.act(tap=['down'], ticks=2)
        before = game.act(tap=['select'], ticks=3)        # "Report a bug": the overlay opens as the tick ends
        assert before['scene'] == 'report' and before['under'] == 'title'
        assert items(before) == ['Send', 'To the pitch', 'Back']          # the title's menu is not seen
        assert 'Report from title (Report a bug)' in hud(before)
        assert any(e['kind'] == 'overlay' and e['name'] == 'report' and e['open'] and e['over'] == 'title'
                   for e in before['events'])
        stood = before['state']['game']['ticks_title']
        later = game.act(ticks=30)
        assert later['state']['game']['ticks_title'] == stood                # nothing of the title runs
        game.act(tap=['down'], ticks=2)
        game.act(tap=['down'], ticks=2)
        back = game.act(tap=['select'], ticks=3)                            # "Back"
        assert back['scene'] == 'title' and 'under' not in back
        assert back['state']['menus'] == [2]                                 # the cursor where it was
        going = game.act(ticks=10)
        assert going['state']['game']['ticks_title'] > stood                 # and the title goes on


def test_a_report_is_posted_and_the_reply_heard(beta, godot, server):
    server.answer = (201, {'number': 7})
    server.received.clear()
    with PlaySession(beta, binary=godot) as game:
        game.act(ticks=3)
        game.act(tap=['down'], ticks=2)                                     # the cursor on "Options"
        opened = game.act(tap=['report'], ticks=3)                          # F9, in any scene
        assert opened['scene'] == 'report' and opened['state']['option'] == 'Options'
        game.act(tap=['select'], ticks=1)                                   # "Send"
        done = game.until({'path': 'state.status', 'op': '==', 'value': 'Report no. 7 sent'}, max_ticks=600)
        assert done['stopped'] == 'condition'
        assert done['state']['game']['reports'] == 1
        (path, kind, body), = server.received
        assert path == '/api/reports' and kind == 'application/json'
        assert body['scene'] == 'title' and body['option'] == 'Options'
        save = json.loads(body['save'])                                     # as a qg:save writes it
        assert save['scene'] == 'title' and save['game']['ticks_title'] == done['state']['game']['ticks_title']
        kinds = [e['kind'] for e in done['events']]
        assert 'posted' in kinds
        closed = game.act(tap=['report'], ticks=3)                          # its action again closes it
        assert closed['scene'] == 'title'


def test_a_refusal_and_no_server_are_reasons(beta, godot, server):
    server.answer = (429, {'error': 'limit', 'message': 'Too many reports'})
    with PlaySession(beta, binary=godot) as game:
        game.act(ticks=3)
        game.act(tap=['report'], ticks=3)
        game.act(tap=['select'], ticks=1)
        refused = game.until({'path': 'state.status', 'op': '!=', 'value': 'Sending'}, max_ticks=600)
        assert refused['state']['status'] == 'Kept: 429: Too many reports'
        assert refused['state']['game']['reports'] == 0
        assert any(e['kind'] == 'post-failed' and e['reason'] == '429: Too many reports' for e in refused['events'])


def test_a_server_that_is_not_there(godot, tmp_path):
    out = build(tmp_path, BETA.replace('SERVER', 'http://127.0.0.1:9/api/reports'))
    with PlaySession(out, binary=godot) as game:
        game.act(ticks=3)
        game.act(tap=['report'], ticks=3)
        game.act(tap=['select'], ticks=1)
        failed = game.until({'path': 'state.status', 'op': '!=', 'value': 'Sending'}, max_ticks=900)
        assert failed['state']['status'] == 'Kept: cannot reach the server'


LATER = '''<q:application id="later" type="game">
  <q:set name="got" value="0" type="number" />
  <q:set name="why" value="" type="string" />
  <q:function name="hello">
    <q:set name="sent_at" value="{'title'}" />
    <qg:post to="SERVER" data="{ {'hello': sent_at} }" timeout="120">
      <qg:on-done><q:set name="got" value="{reply.number}" /><q:set name="why" value="{sent_at}" /></qg:on-done>
    </qg:post>
  </q:function>
  <qg:scene name="title" width="320" height="180">
    <q:call function="hello" />
    <qg:timer after="2"><qg:goto-scene name="pitch" /></qg:timer>
  </qg:scene>
  <qg:scene name="pitch" width="320" height="180">
    <q:set name="here" value="0" type="number" />
  </qg:scene>
</q:application>
'''


def test_an_answer_to_a_function_of_the_game_is_heard_by_the_scene_played_then(godot, server, tmp_path):
    """The title sends, and is left before the server answers: the answer is heard in the pitch, which has the
    application's q:function too, with the names of its handler as they were. (The play protocol runs at a fixed 60
    frames a second of game time, as fast as it can: the timeout is of those seconds, and is long here.)"""
    server.answer, server.delay = (201, {'number': 12}), 0.5
    try:
        out = build(tmp_path, LATER.replace('SERVER', server.url))
        with PlaySession(out, binary=godot) as game:
            left = game.act(ticks=6)
            assert left['scene'] == 'pitch' and left['state']['game']['got'] == 0       # not answered yet
            heard = game.until({'path': 'state.game.got', 'op': '==', 'value': 12}, max_ticks=6000)
            assert heard['stopped'] == 'condition' and heard['scene'] == 'pitch'
            assert heard['state']['game']['why'] == 'title'
    finally:
        server.delay = 0.0


def test_a_scene_change_from_the_overlay_closes_it(beta, godot):
    with PlaySession(beta, binary=godot) as game:
        game.act(ticks=3)
        game.act(tap=['report'], ticks=3)
        game.act(tap=['down'], ticks=2)
        moved = game.act(tap=['select'], ticks=3)                           # "To the pitch"
        assert moved['scene'] == 'pitch' and 'under' not in moved
        assert any(e['kind'] == 'overlay' and not e['open'] for e in moved['events'])
        again = game.act(tap=['report'], ticks=3)                           # and opens over the pitch too
        assert again['scene'] == 'report' and again['under'] == 'pitch' and again['state']['seen'] == 'pitch'
        assert again['state']['option'] == ''                               # the pitch has no menu


def test_the_report_button_is_on_every_screen(beta, godot):
    with PlaySession(beta, binary=godot) as game:
        title = game.act(ticks=3)
        assert PlaySession.screen(title, 'touch')['controls'][0]['action'] == 'report'
        pitch = game.act(tap=['select'], ticks=3)
        assert pitch['scene'] == 'pitch'
        assert PlaySession.screen(pitch, 'touch')['controls'][0]['action'] == 'report'


@pytest.mark.parametrize('change, error', [
    ('<qg:overlay name="report"', '<qg:overlay name="title"'),
])
def test_an_overlay_named_as_a_scene_is_refused(tmp_path, change, error):
    with pytest.raises(GameCompileError, match='a scene has that name'):
        build(tmp_path, BETA.replace('SERVER', 'https://example.com/r').replace(change, error)
              .replace('<qg:open-overlay name="report"', '<qg:open-overlay name="title"'))


@pytest.mark.parametrize('change, message', [
    (('<qg:open-overlay name="report" />', '<qg:open-overlay name="help" />'), 'no qg:overlay of that name'),
    (('action="report" shade', 'action="help" shade'), 'no such action'),
    (('shade="0.5"', 'shade="2"'), '0 \\(the scene as it is\\) to 1'),
    (('value="SERVER"', 'value="x"'), None),
    (('to="{server}"', 'to="ftp://example.com"'), 'an http:// or https:// address'),
    (('timeout="5"', 'timeout="0"'), 'more than 0'),
    (('<qg:on-fail>', '<qg:on-done></qg:on-done><qg:on-fail>'), 'one <qg:on-done> and one <qg:on-fail>'),
    (('<qg:menu>\n      <qg:button label="Send">', '<qg:character id="x" controller="platformer" />\n'
                                                   '    <qg:menu>\n      <qg:button label="Send">'),
     'cannot go inside <overlay>'),
])
def test_what_is_refused(tmp_path, change, message):
    source = BETA.replace('SERVER', 'https://example.com/r').replace(*change)
    if message is None:
        build(tmp_path, source)
        return
    with pytest.raises(GameCompileError, match=message):
        build(tmp_path, source)


def test_not_in_a_multiplayer_game(tmp_path):
    source = BETA.replace('SERVER', 'https://example.com/r').replace(
        '<qg:input action="report" keys="F9" />',
        '<qg:input action="report" keys="F9" /><qg:multiplayer players="2" />')
    with pytest.raises(GameCompileError, match='not in a qg:multiplayer game'):
        build(tmp_path, source)
    posting = '''<q:application id="scores" type="game">
  <qg:multiplayer players="2" />
  <qg:scene name="title">
    <qg:menu><qg:button label="Send"><qg:post to="https://example.com/scores" data="{ {'a': 1} }" /></qg:button></qg:menu>
  </qg:scene>
</q:application>
'''
    with pytest.raises(GameCompileError, match='is not for a qg:multiplayer game'):
        build(tmp_path, posting)
