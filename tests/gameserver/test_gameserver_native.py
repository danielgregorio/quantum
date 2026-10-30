"""The Rust engine (PLAN_WORLD_ENGINE.md, E1): native/world, the module quantum_world, built by maturin.

The same log on both engines tells each player the same, to the byte, on every test world; a world served on it
checks what a player sends as the Python server does (the whole of tests/gameserver, and the Godot world tests, run
on it in CI with QUANTUM_WORLD_ENGINE=rust: .github/workflows/world-engine.yml); its numbers say what the engine
took; and where it is not built, a world asked to run on it runs on Python, and says so.
"""

import json
import random
import time

import pytest
from test_gameserver_conform import WORLDS, definition_of, session

from quantum.runtime.gameserver import native
from quantum.runtime.gameserver.conform import ENGINES, conform, inputs_of
from quantum.runtime.gameserver.server import WorldServer, make_server
from quantum.runtime.gameserver.session import WorldSession, serve_world

needs_rust = pytest.mark.skipif(not native.available(), reason=f'the Rust engine is not built here ({native.BUILD})')
YARD = WORLDS['meadow'].parents[1] / 'yard' / 'yard.server.q'


@needs_rust
@pytest.mark.parametrize('name', sorted(WORLDS))
def test_the_rust_engine_tells_each_player_what_python_tells_them_to_the_byte(name):
    """Twenty players, three hundred ticks of every command, coming and going: on each tick, each player's messages
    from the engine are the very texts the Python server would write."""
    definition = definition_of(name)
    entries, world = session(definition, ticks=300, players=20, seed=23)
    report = conform(definition, None, entries, ['python', 'rust'], digest_every=10)
    assert report.same, '\n'.join(map(str, report.differences))
    python, rust = ENGINES['python'](definition), ENGINES['rust'](definition)
    by_tick = {}
    for e in entries:
        by_tick.setdefault(e['t'], []).append(e)
    told = 0
    for tick in range(1, world.tick + 1):
        inputs = inputs_of(by_tick.get(tick, []))
        frames = python.step(inputs)['frames']
        rust.step(inputs)
        assert set(frames) == set(rust.texts), tick
        for account, said in frames.items():
            assert [json.dumps(m, separators=(',', ':')) for m in said] == rust.texts[account], (tick, account)
            told += len(said)
    assert told > 1000 and python.digest() == rust.digest()


@needs_rust
def test_a_world_on_the_rust_engine_checks_what_a_player_sends():
    from websockets.sync.client import connect

    def said(ws, message) -> dict:
        ws.send(message if isinstance(message, str) else json.dumps(message))
        return json.loads(ws.recv(timeout=5))

    with serve_world(YARD, step=False, engine='rust') as server:
        assert server.engine_name == 'rust'
        with connect(server.url) as ws:
            assert said(ws, {'type': 'cmd', 'seq': 1, 'name': 'step'}) == {'type': 'error', 'reason': 'Say hello first.'}
        with connect(server.url) as ws:
            assert said(ws, 'not json')['reason'] == 'A message is a JSON object with a type.'
        with connect(server.url) as ws:
            assert said(ws, {'type': 'hello', 'name': 'a name with spaces'})['reason'] == ('A name is 1 to 24 letters, '
                                                                                        'digits, _ or -.')
        with WorldSession(server.url, 'ana') as ana:
            pong = said(ana.ws, {'type': 'ping', 't': 12.5})
            while pong['type'] != 'pong':                                      # the world's ticks come too
                pong = json.loads(ana.ws.recv(timeout=5))
            assert pong['t'] == 12.5 and pong['tick'] >= 1
            seen = ana.until(lambda o: o['me']['at'] == {'x': 2, 'y': 1}, send=[('step', {'dir': 'east'})])
            assert seen['until']
            assert server.stats()['engine'] == 'rust'
        with WorldSession(server.url, 'bo') as bo:
            for n in range(70):                                                  # more than sixty in a second
                bo.ws.send(json.dumps({'type': 'ping', 't': n}))
            reason = None
            deadline = time.monotonic() + 5
            while reason is None and time.monotonic() < deadline:
                message = json.loads(bo.ws.recv(timeout=5))
                reason = message.get('reason') if message['type'] == 'error' else None
            assert reason == 'More than 60 messages a second.'
        with WorldSession(server.url, 'cy') as cy:
            cy.ws.send(json.dumps({'type': 'cmd', 'seq': 1, 'name': 'step', 'args': {'dir': 'x' * 20_000}}))
            with pytest.raises(Exception):                                     # past 16 KB: closed, as websockets does
                for _ in range(100):
                    cy.ws.recv(timeout=5)
        deadline = time.monotonic() + 5
        while server.world.players and time.monotonic() < deadline:             # each one that was closed has left
            time.sleep(0.05)
        assert not server.world.players


@needs_rust
def test_the_rust_engines_numbers_say_its_share_of_the_tick():
    rng = random.Random(4)
    with serve_world(definition_of('meadow'), engine='rust') as served:
        with WorldSession(served.url, 'ana') as ana:
            for _ in range(5):
                ana.act(send=[('step', {'dir': rng.choice(['north', 'south', 'east', 'west'])})], ticks=2)
            numbers = served.stats()
    assert type(served).__name__ == 'NativeServer'
    assert numbers['engine'] == 'rust' and numbers['players'] == 1
    assert {'bridge_ms_p50', 'frames_ms_p50', 'write_ms_p50', 'step_ms_p50', 'send_ms_p50'} <= set(numbers)


def test_where_it_is_not_built_a_world_runs_on_python_and_says_so(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(native, 'quantum_world', None)
    server = make_server(definition_of('meadow'), 'rust', quiet=False, data_dir=tmp_path)
    assert type(server) is WorldServer and server.engine_name == 'python'
    assert 'the Rust engine is not built here (pip install ./native/world)' in capsys.readouterr().out
    monkeypatch.setenv(native.ENGINE_ENV, 'nope')
    with pytest.raises(ValueError, match="no engine 'nope'"):
        make_server(definition_of('meadow'), quiet=True, data_dir=tmp_path)
    monkeypatch.setenv(native.ENGINE_ENV, 'python')
    assert type(make_server(definition_of('meadow'), quiet=True, data_dir=tmp_path)) is WorldServer
