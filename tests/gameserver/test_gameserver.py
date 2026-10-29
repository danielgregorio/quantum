"""The game server, Phase 1 of PLAN_GAME_SERVER.md: the world lives.

A world is read against its schema (and says what it does not have, with its line); a player comes in as a guest
and steps; the world refuses a wall, a step before the last ended, a command sent faster than its limit and a forged
one, and a refused command leaves nothing; two players see the same world and not each other's private fields; the
same inputs make the same world; and a server killed mid-way, started again, has every command it acknowledged.
"""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.gameserver import GameServerError, World, read_world
from quantum.runtime.gameserver.log import WorldLog, replay
from quantum.runtime.gameserver.session import WorldSession, WorldSessionError, serve_world

REPO = Path(__file__).resolve().parents[2]
YARD = Path(__file__).resolve().parent / 'worlds' / 'yard' / 'yard.server.q'
TMX = YARD.parent / 'yard.tmx'


def world_of(tmp_path, body, head='<q:map name="yard" tiled="{tmx}" />'):
    """A world written for a test, on the yard's map."""
    path = tmp_path / 'test.server.q'
    path.write_text(f'<q:application id="t" type="gameserver">\n  <q:gameserver name="t">\n    '
                    f'{head.format(tmx=TMX)}\n{body}\n  </q:gameserver>\n</q:application>\n')
    return read_world(QuantumParser(use_cache=False).parse_file(str(path)), str(path))


HERO = '<q:entity name="hero" kind="Hero" per-player="true" />'


# --- the file ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize('body, says, line', [
    (HERO + '\n<q:director every="10m" />', '<q:director> is not a tag of a world', 5),     # Phase 6's
    (HERO + '\n<q:command name="go" speed="2"></q:command>', 'has no attribute speed=', 5),
    (HERO + '\n<q:command name="go" limit="fast"></q:command>', 'limit= is so many in so long', 5),
    (HERO + '\n<q:command name="go"><q:require condition="{me.at ==}" /></q:command>', 'invalid expression', 5),
    (HERO + '\n<q:command name="go"><q:field name="x" /></q:command>', '<q:field> goes in q:entity', 5),
    (HERO + '\n<q:every interval="2 seconds"></q:every>', 'is a time', 5),
    ('<q:entity name="a" kind="A" />', 'one entity with per-player="true"', 2),
    (HERO + '\n<q:command name="go">text</q:command>', 'holds text', 5),
])
def test_the_schema_says_what_a_world_does_not_have(tmp_path, body, says, line):
    with pytest.raises(GameServerError) as e:
        world_of(tmp_path, body)
    assert says in e.value.message and e.value.line == line, str(e.value)


def test_a_world_needs_its_map_and_the_map_its_file(tmp_path):
    with pytest.raises(GameServerError, match='needs its q:map'):
        world_of(tmp_path, HERO, head='')
    with pytest.raises(GameServerError, match='there is no such file'):
        world_of(tmp_path, HERO, head='<q:map name="m" tiled="nowhere.tmx" />')


def test_the_yard_reads_and_the_check_says_so():
    world = read_world(QuantumParser(use_cache=False).parse_file(str(YARD)), str(YARD))
    assert (world.map.width, world.map.height) == (12, 8)
    assert (5, 3) in world.map.walls and (0, 0) in world.map.walls and (1, 1) not in world.map.walls
    assert world.map.areas['gate'] == (1, 1, 2, 2) and world.map.areas['pen'] == (8, 4, 10, 6)
    assert world.hero.step_ticks == 3                        # four steps a second at ten ticks a second
    assert world.commands['step'].limit == (8, 10)
    done = subprocess.run([sys.executable, '-m', 'quantum.cli.runner', 'gameserver', 'check', str(YARD)],
                          capture_output=True, text=True, cwd=REPO)
    assert done.returncode == 0 and '[OK] yard' in done.stdout, done.stdout + done.stderr


def test_a_gameserver_is_laboratory():
    from quantum.core import tiers
    assert 'gameserver' in tiers.LAB_APP_TYPES


# --- a player in the world ----------------------------------------------------------------------------------------

def test_a_player_comes_in_at_the_gate_and_steps():
    with serve_world(YARD) as server, WorldSession(server.url, 'ana') as ana:
        assert ana.me_id == 'hero:ana' and ana.welcome['world'] == 'yard' and ana.welcome['map'] == 'yard.tmx'
        seen = ana.observe()
        assert seen['me']['at'] == {'x': 1, 'y': 1} and seen['me']['name'] == 'ana'
        seen = ana.act(send=[('step', {'dir': 'east'})], ticks=1)
        assert seen['acks'] == [1] and seen['me']['at'] == {'x': 2, 'y': 1} and seen['me']['facing'] == 'east'
        assert seen['me']['steps'] == 1
        assert server.world.vars['visits'] == 1


def test_a_wall_a_step_too_soon_and_a_command_too_fast_are_refused():
    with serve_world(YARD) as server, WorldSession(server.url, 'ana') as ana:
        seen = ana.act(send=[('step', {'dir': 'north'})], ticks=1)      # the yard's wall
        assert seen['refused'] == [{'seq': 1, 'name': 'step', 'reason': 'A wall.'}]
        seen = ana.act(send=[('step', {'dir': 'east'}), ('step', {'dir': 'east'})], ticks=1)
        assert seen['acks'] == [2] and seen['refused'][0]['reason'] == 'Still moving.'
        assert seen['me']['at'] == {'x': 2, 'y': 1}
        seen = ana.act(ticks=3)
        seen = ana.act(send=[('step', {'dir': 'east'})], ticks=1)       # the step's three ticks are over
        assert seen['me']['at'] == {'x': 3, 'y': 1}
        ana.act(send=[('go', {'to': 'pen'})], ticks=1)
        seen = ana.act(send=[('pick', {}), ('pick', {})], ticks=1)      # one a second
        assert seen['acks'] == [6] and seen['refused'] == [{'seq': 7, 'name': 'pick', 'reason': 'Too fast.'}]
        ana.act(ticks=10)                                                # a second later, another
        seen = ana.act(send=[('pick', {})], ticks=1)
        assert seen['acks'] == [8]


def test_a_forged_command_is_refused_and_one_out_of_the_protocol_closes():
    with serve_world(YARD) as server:
        with WorldSession(server.url, 'ana') as ana:
            seen = ana.act(send=[('step', {}), ('step', {'dir': 'east', 'far': 9}), ('fly', {}),
                                 ('step', {'dir': {'a': {'b': {'c': 1}}}}), ('step', {'dir': 'x' * 3000})],
                           ticks=1)
            reasons = [r['reason'] for r in seen['refused']]
            assert reasons == ['step takes dir.', 'step takes dir.', "There is no command 'fly'.",
                               'step: an argument is not a plain value.', 'step: an argument is not a plain value.']
            assert seen['me']['at'] == {'x': 1, 'y': 1} and seen['me']['steps'] == 0
            ana.ws.send(json.dumps({'type': 'cmd', 'seq': 'one', 'name': 'step', 'args': {'dir': 'east'}}))
            with pytest.raises(WorldSessionError, match='integer seq'):
                ana.observe()
        with WorldSession(server.url, 'ana') as again:          # the connection closed, its player left: back in
            assert again.me_id == 'hero:ana' and list(server.world.players) == ['ana']
        with pytest.raises(WorldSessionError, match='1 to 24 letters'):
            WorldSession(server.url, 'a name with spaces')


def test_a_refused_command_leaves_nothing():
    with serve_world(YARD) as server, WorldSession(server.url, 'ana') as ana:
        seen = ana.act(send=[('pick', {})], ticks=1)                   # a coin, then "No coin here": undone
        assert seen['refused'][0]['reason'] == 'No coin here.' and seen['me']['coins'] == 0
        assert server.world.entities['hero:ana']['coins'] == 0


def test_two_players_see_the_same_world_and_not_each_others_private_fields():
    with serve_world(YARD) as server, WorldSession(server.url, 'ana') as ana, WorldSession(server.url, 'bo') as bo:
        ana.act(send=[('step', {'dir': 'south'})], ticks=1)
        mine, theirs = ana.observe(), bo.observe()
        assert theirs['world']['hero:ana']['at'] == mine['me']['at'] == {'x': 1, 'y': 2}
        assert 'coins' in mine['me'] and 'coins' not in theirs['world']['hero:ana']
        assert set(theirs['world']) == set(mine['world']) == {'hero:ana', 'hero:bo'}
        assert not any(k.startswith('_') for e in theirs['world'].values() for k in e)


def test_functions_loops_and_a_rule_every_second():
    with serve_world(YARD) as server, WorldSession(server.url, 'ana') as ana:
        seen = ana.act(send=[('tally', {'n': 4})], ticks=1)
        assert seen['me']['coins'] == 10                                # 1 + 2 + 3 + 4
        ana.act(send=[('go', {'to': 'pen'})], ticks=1)
        before = ana.observe()['me']['coins']
        seen = ana.until('me.coins >= ' + str(before + 2), max_ticks=40)
        assert seen['until'] and seen['tick'] % 10 == 0                 # a coin on each tenth tick


def test_a_player_who_leaves_is_kept_and_comes_back_where_they_were():
    with serve_world(YARD) as server:
        with WorldSession(server.url, 'ana') as ana:
            ana.act(send=[('step', {'dir': 'east'})], ticks=4)
            ana.act(send=[('step', {'dir': 'south'})], ticks=1)
        with WorldSession(server.url, 'bo') as bo:                      # bo's join is the tick ana leaves on
            assert 'hero:ana' not in bo.observe()['world']
        assert server.world.stored['ana']['at'] == {'x': 2, 'y': 2}
        with WorldSession(server.url, 'ana') as ana:
            seen = ana.observe()
            assert seen['me']['at'] == {'x': 2, 'y': 2} and seen['me']['steps'] == 2
        assert server.world.vars['visits'] == 3


def test_the_world_is_full():
    with serve_world(YARD) as server:                                    # players="3"
        sessions = [WorldSession(server.url, n) for n in ('a', 'b', 'c')]
        with pytest.raises(WorldSessionError, match='The world is full'):
            WorldSession(server.url, 'd')
        for s in sessions:
            s.close()


def test_a_live_world_ticks_by_itself():
    with serve_world(YARD, step=False) as server, WorldSession(server.url, 'ana') as ana:
        assert not ana.step_mode
        seen = ana.act(send=[('step', {'dir': 'east'})], ticks=3)
        assert seen['acks'] == [1] and seen['me']['at'] == {'x': 2, 'y': 1}
        with pytest.raises(WorldSessionError, match='keeps its own time'):
            ana._send({'type': 'step', 'ticks': 1})
            ana.observe()


def test_a_rule_that_fails_is_kept_and_the_world_goes_on(tmp_path):
    definition = world_of(tmp_path, HERO + '''
      <q:set name="n" value="0" />
      <q:every interval="100ms"><q:set name="n" value="{n + 1}" /><q:set name="m" value="{nothing.x}" /></q:every>
      <q:every interval="100ms"><q:set name="n" value="{n + 10}" /></q:every>''')
    world = World(definition)
    for _ in range(3):
        world.step([])
    assert world.vars['n'] == 30                                        # the failing rule's +1 was undone
    assert len(world.errors) == 3 and "'nothing' is not defined" in world.errors[0]['message']
    assert world.errors[0]['where'] == 'q:every' and world.errors[0]['line'] == 6


# --- the same inputs, the same world; and the log ----------------------------------------------------------------

INPUTS = [[('join', 'ana')], [('cmd', 'ana', 1, 'step', {'dir': 'east'})], [], [], [],
          [('join', 'bo'), ('cmd', 'ana', 2, 'step', {'dir': 'south'}), ('cmd', 'bo', 1, 'pick', {})],
          [('cmd', 'ana', 3, 'go', {'to': 'pen'})]] + [[]] * 25 + [[('leave', 'bo')]]


def test_the_same_inputs_make_the_same_world():
    definition = read_world(QuantumParser(use_cache=False).parse_file(str(YARD)), str(YARD))
    worlds = [World(definition), World(definition)]
    for inputs in INPUTS:
        for w in worlds:
            w.step(inputs)
    assert worlds[0].digest() == worlds[1].digest()
    assert worlds[0].entities['hero:ana']['coins'] == 3 and 'bo' in worlds[0].stored


def test_a_snapshot_and_the_inputs_after_it_are_the_world(tmp_path):
    definition = read_world(QuantumParser(use_cache=False).parse_file(str(YARD)), str(YARD))
    whole = World(definition)
    log = WorldLog(tmp_path)
    log.open(0)
    for i, inputs in enumerate(INPUTS):
        out = whole.step(inputs)
        log.append(out.entries)
        log.flush()
        if i == 3:
            log.write_snapshot(whole)
    snap, entries = log.load()
    assert snap['tick'] == 4 and entries and all(e['t'] > 4 for e in entries)
    again = World.from_snapshot(definition, snap)
    assert replay(again, entries) == []
    while again.tick < whole.tick:
        again.step([])
    assert again.digest() == whole.digest()


def test_a_server_killed_mid_way_has_every_command_it_acknowledged(tmp_path):
    from quantum.runtime.godot_replay import free_port
    port = free_port()
    data = tmp_path / 'data'

    def start():
        process = subprocess.Popen([sys.executable, '-m', 'quantum.cli.runner', 'gameserver', 'run', str(YARD),
                                    '--step', '--port', str(port), '--data', str(data)],
                                   cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            if f'ws://127.0.0.1:{port}' in line:
                return process
        raise AssertionError('the server did not start: ' + (process.stdout.read() if process.stdout else ''))

    server = start()
    try:
        with WorldSession(f'ws://127.0.0.1:{port}', 'ana') as ana:
            seen = ana.act(send=[('step', {'dir': 'east'})], ticks=4)
            seen = ana.act(send=[('step', {'dir': 'east'})], ticks=4)
            seen = ana.act(send=[('tally', {'n': 3})], ticks=1)
            assert seen['acks'] == [3] and seen['me']['at'] == {'x': 3, 'y': 1} and seen['me']['coins'] == 6
            tick = seen['tick']
            os.kill(server.pid, signal.SIGKILL)                        # no snapshot: only the log
            server.wait(10)
    finally:
        if server.poll() is None:
            server.kill()
    assert not (data / 'snapshot.json').exists()
    server = start()
    try:
        with WorldSession(f'ws://127.0.0.1:{port}', 'ana') as ana:
            seen = ana.observe()
            assert seen['me']['at'] == {'x': 3, 'y': 1} and seen['me']['coins'] == 6 and seen['me']['steps'] == 2
            assert seen['tick'] > tick
    finally:
        server.send_signal(signal.SIGTERM)
        try:
            said, _ = server.communicate(timeout=60)                      # a loaded machine stops slowly
        except subprocess.TimeoutExpired:
            server.kill()
            said, _ = server.communicate()
    assert (data / 'snapshot.json').exists(), f'no snapshot after the stop; the server said: {said}'   # a stop writes the world
