"""quantum relay: two players meet in a room and play the same game.

The relay starts the room's Godot (a host with no seat) when the first
player arrives, carries each player's messages to it unchanged, and stops it
when the last one leaves. The game through it is the same as when player 1
hosts.
"""

import asyncio
import contextlib
import logging
import threading
from pathlib import Path

import pytest

pytest.importorskip('websockets')

from quantum.runtime.game_relay import GameRelay  # noqa: E402
from quantum.runtime.godot_replay import replay_peers, tape_from_holds  # noqa: E402

PROJECTS = Path(__file__).resolve().parents[2] / 'projects'


@contextlib.contextmanager
def serving(game_relay, cert=None, key=None):
    """A relay on its own event loop in a thread: it is made, served and closed on that
    loop. Answers its address (ws:// or wss://). It listens on a port the system gives it
    (port 0): a port picked first and bound later could be taken in between by another
    test's game, running alongside (a TLS client then reached a plain WebSocket)."""
    loop = asyncio.new_event_loop()
    ready = threading.Event()
    box = {}

    def run():
        asyncio.set_event_loop(loop)
        box['server'] = loop.run_until_complete(game_relay.serve('127.0.0.1', 0, cert, key))
        box['port'] = next(iter(box['server'].sockets)).getsockname()[1]
        ready.set()
        loop.run_forever()
        box['server'].close()
        loop.run_until_complete(box['server'].wait_closed())
        loop.close()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    assert ready.wait(30)
    try:
        yield f'{"wss" if cert else "ws"}://127.0.0.1:{box["port"]}'
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(10)


@pytest.fixture(scope='module')
def relay(godot):
    game_relay = GameRelay(projects=PROJECTS, binary=godot)
    with serving(game_relay) as url:
        yield game_relay, url
    game_relay.shutdown()


def test_two_players_meet_in_a_room_and_play_the_same_game(relay, godot):
    game_relay, url = relay
    player1 = tape_from_holds([('down', 0, 60)])
    player2 = tape_from_holds([('up', 0, 60), ('up', 100, 200)])
    project = game_relay.build('pong')
    peers = replay_peers(project, 300, [player1, player2], binary=godot, relay=f'{url}/pong/test-room')
    assert peers[0] == peers[1]
    hosted = replay_peers(project, 300, [player1, player2], binary=godot, transport='websocket')
    assert peers[0]['court'] == hosted[0]['court']


def test_the_room_closes_when_its_players_leave(relay, godot):
    game_relay, url = relay
    project = game_relay.build('pong')
    replay_peers(project, 60, [{}, {}], binary=godot, relay=f'{url}/pong/brief')
    for _ in range(50):
        if 'pong/brief' not in game_relay.rooms:
            break
        threading.Event().wait(0.1)
    assert 'pong/brief' not in game_relay.rooms


def test_what_it_refuses(relay):
    import websockets.sync.client as client
    game_relay, url = relay
    for path, reason in [('/nowhere', 'the address is /game/room'), ('/rpg/room', 'not a networked game'),
                         ('/nothing/room', "no game named 'nothing'")]:
        with client.connect(url + path) as ws:
            with pytest.raises(Exception):
                ws.recv(timeout=10)
            assert reason in (ws.close_reason or '')


def test_with_a_certificate_it_is_wss(godot, tmp_path, caplog):
    # a page served over HTTPS may only open wss://: given a certificate, the relay speaks TLS
    import ssl
    import subprocess

    import websockets
    import websockets.sync.client as client
    caplog.set_level(logging.DEBUG, logger='websockets')
    cert, key = tmp_path / 'cert.pem', tmp_path / 'key.pem'
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1', '-subj', '/CN=localhost',
                    '-keyout', str(key), '-out', str(cert)], check=True, capture_output=True)
    game_relay = GameRelay(projects=PROJECTS, binary=godot)
    try:
        with serving(game_relay, str(cert), str(key)) as url:
            assert url.startswith('wss://')
            trust = ssl.create_default_context(cafile=str(cert))
            trust.check_hostname = False
            # a loaded CI runner (tests side by side, Godots running) has dropped a TLS opening
            # once in a while: the connection is tried three times, and the server's own log
            # (websockets.server) is in the report if it still fails
            for attempt in range(3):
                try:
                    with client.connect(f'{url}/nowhere', ssl=trust, open_timeout=30) as ws:
                        with pytest.raises(Exception):
                            ws.recv(timeout=10)
                        assert ws.close_reason == 'the address is /game/room'
                    break
                except (OSError, websockets.exceptions.InvalidMessage):
                    if attempt == 2:
                        raise
    finally:
        game_relay.shutdown()


def test_a_plain_request_is_a_health_check(relay):
    # what a host (Fly.io, Render) asks to know the relay is up: no WebSocket, an answer in JSON
    import json
    import urllib.request
    game_relay, url = relay
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url.replace('ws://', 'http://') + '/health', timeout=10) as answer:
        health = json.loads(answer.read())
    assert health['relay'] == 'quantum' and health['games'] == ['arena', 'chess', 'delve', 'pong', 'towers']
    assert health['rooms'] == len(game_relay.rooms)
