"""The game server, Phase 2 of PLAN_GAME_SERVER.md: what each player sees.

A view (q:view) is what a player sees of the world, and only what changes in it is sent: what came in, the fields
that changed, what left. A hero's private field never reaches another player. A view near the player reads the
world's index (cells of 16 tiles), and what it sends is the same as reading the whole world would give: a hundred
ticks of forty players walking and jumping are checked against that. An event (q:emit) goes to whoever sees where
it happened, to one player, or to everyone, and a refused command's never. A test's harness steps the world on a
control connection, with no entity of its own, and peeks at the whole of it.
"""

import asyncio
import json
import random
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.gameserver import GameServerError, World, read_world
from quantum.runtime.gameserver.server import WorldServer
from quantum.runtime.gameserver.session import WorldSession, WorldSessionError, serve_world
from quantum.runtime.gameserver.world import CELL

MEADOW = Path(__file__).resolve().parent / 'worlds' / 'meadow' / 'meadow.server.q'
TMX = MEADOW.parent / 'meadow.tmx'


def meadow():
    return read_world(QuantumParser(use_cache=False).parse_file(str(MEADOW)), str(MEADOW))


def world_of(tmp_path, body):
    path = tmp_path / 'test.server.q'
    path.write_text(f'<q:application id="t" type="gameserver">\n  <q:gameserver name="t">\n    '
                    f'<q:map name="m" tiled="{TMX}" />\n'
                    f'<q:entity name="hero" kind="Hero" per-player="true" />\n{body}\n  </q:gameserver>\n'
                    f'</q:application>\n')
    return read_world(QuantumParser(use_cache=False).parse_file(str(path)), str(path))


# --- the file ---------------------------------------------------------------------------------------------------

def test_a_view_near_the_player_reads_the_index_and_one_of_anything_else_reads_the_world():
    views = meadow().views
    assert (views['around'].radius, views['around'].rest) == (5, False)
    assert (views['loud'].radius, views['loud'].rest) == (None, True)
    assert meadow().reach is None                      # a view of the whole world: an event at a place reaches all


def test_a_world_with_no_view_sees_it_whole(tmp_path):
    world = world_of(tmp_path, '')
    assert list(world.views) == ['world'] and world.views['world'].where is None


@pytest.mark.parametrize('where, says', [
    ('{near(it, me, 5) and chance(0.5)}', 'calls chance()'),
    ('{random(1, 2) == 1}', 'calls random()'),
    ('{mine(it)}', 'calls mine()'),
])
def test_a_view_changes_nothing(tmp_path, where, says):
    with pytest.raises(GameServerError, match=says):
        world_of(tmp_path, f'<q:view name="v" where="{where}" />\n'
                           '<q:function name="mine" params="x"><q:return value="{true}" /></q:function>')


def test_a_record_in_braces_is_a_record(tmp_path):
    world = world_of(tmp_path, '<q:set name="r" value="{ {\'a\': 1} }" />')
    assert World(world).vars['r'] == {'a': 1}


# --- views, through the protocol --------------------------------------------------------------------------------

def test_two_players_see_each_other_come_into_view_and_leave_it():
    with serve_world(MEADOW) as server:
        with WorldSession(server.url, 'ana') as ana, WorldSession(server.url, 'bo') as bo:
            seen = ana.act(send=[('go', {'to': 'east'})], ticks=1)
            assert seen['me']['at'] == {'x': 41, 'y': 27}
            assert 'hero:bo' not in seen['world']               # bo is at the west, 38 tiles away
            assert 'hero:ana' not in bo.observe()['views']['around']
            seen = ana.act(send=[('go', {'to': {'x': 8, 'y': 4}})], ticks=1)
            assert 'hero:bo' in seen['views']['around']        # bo at (3, 3): five tiles
            assert bo.observe()['views']['around']['hero:ana']['at'] == {'x': 8, 'y': 4}
            seen = ana.act(send=[('step', {'dir': 'east'})], ticks=2)
            assert seen['me']['at'] == {'x': 9, 'y': 4} and 'hero:bo' not in seen['world']   # six: out of view
            assert 'hero:ana' not in bo.observe()['world']
            seen = ana.act(send=[('step', {'dir': 'west'})], ticks=2)
            assert seen['world']['hero:bo'] == {'id': 'hero:bo', 'kind': 'Hero', 'at': {'x': 3, 'y': 3},
                                                'facing': 'south', 'name': 'bo', 'mood': 'calm'}


def test_an_update_holds_only_what_changed_and_a_private_field_only_its_player_has():
    with serve_world(MEADOW) as server:
        with WorldSession(server.url, 'ana') as ana, WorldSession(server.url, 'bo', keep_frames=True) as bo:
            ana.act(send=[('earn', {}), ('earn', {})], ticks=1)
            seen = ana.observe()
            assert seen['me']['purse'] == 2
            other = bo.observe()['world']['hero:ana']
            assert 'purse' not in other and other['name'] == 'ana'
            ana.act(send=[('step', {'dir': 'east'})], ticks=1)
            bo.observe()
            frames = [f for f in bo.frames if f.get('type') == 'tick']
            of_ana = [e for f in frames for v in f.get('views', {}).values()
                      for e in v.get('enter', []) + v.get('update', []) if e['id'] == 'hero:ana']
            assert of_ana and all('purse' not in e for e in of_ana), of_ana
            assert set(of_ana[-1]) == {'id', 'at', 'facing'}, of_ana     # it moved, and faces east: no more
            # what changed of ana's purse goes to ana, and no one else hears of it: a test world says each tick to
            # everyone, and bo's three say nothing more
            before = len([f for f in bo.frames if f.get('type') == 'tick'])
            ana.act(send=[('earn', {})], ticks=3)
            bo.observe()
            new = [f for f in bo.frames if f.get('type') == 'tick'][before:]
            assert len(new) == 3 and all(set(f) == {'type', 'tick'} for f in new), new


def test_a_view_of_the_whole_world_with_a_condition():
    with serve_world(MEADOW) as server:
        with WorldSession(server.url, 'ana') as ana, WorldSession(server.url, 'bo') as bo:
            bo.act(send=[('go', {'to': 'east'})], ticks=1)
            assert ana.observe()['views']['loud'] == {}
            bo.act(send=[('shout', {'text': 'hey'})], ticks=1)
            loud = ana.observe()['views']['loud']
            assert list(loud) == ['hero:bo'] and 'hero:bo' not in ana.observe()['views']['around']
            bo.act(send=[('hush', {})], ticks=1)
            assert ana.observe()['views']['loud'] == {}


# --- events -----------------------------------------------------------------------------------------------------

def test_an_event_goes_to_whoever_sees_where_it_happened_to_one_or_to_all(tmp_path):
    near = tmp_path / 'near.server.q'      # the meadow, with only the view near: an event's reach is five tiles
    near.write_text(MEADOW.read_text().replace(
        '<q:view name="loud" where="{it.kind == \'Hero\' and it.mood == \'loud\'}" />', '')
        .replace('tiled="meadow.tmx"', f'tiled="{TMX}"'))
    with serve_world(near) as server:
        with WorldSession(server.url, 'ana') as ana, WorldSession(server.url, 'bo') as bo, \
                WorldSession(server.url, 'cy') as cy:
            cy.act(send=[('go', {'to': 'east'})], ticks=1)
            heard = ana.act(send=[('shout', {'text': 'over here'})], ticks=1)['events']
            assert heard == [{'name': 'shout', 'value': 'ana: over here', 'at': {'x': 3, 'y': 3}, 'of': 'hero:ana'}]
            assert bo.observe()['events'] == heard and cy.observe()['events'] == []
            assert ana.act(send=[('whisper', {'to': 'hero:cy', 'text': 'psst'})], ticks=1)['events'] == []
            assert cy.observe()['events'] == [{'name': 'whisper', 'value': {'from': 'ana', 'text': 'psst'}}]
            assert bo.observe()['events'] == []
            assert [e['name'] for e in cy.act(send=[('ring', {})], ticks=1)['events']] == ['bell']
            assert [e['name'] for e in ana.observe()['events']] == ['bell']
            assert [e['name'] for e in bo.observe()['events']] == ['bell']
            seen = ana.act(send=[('boast', {})], ticks=1)
            assert seen['refused'][0]['reason'] == 'Not rich enough.' and seen['events'] == []
            assert bo.observe()['events'] == []


# --- the harness's door -----------------------------------------------------------------------------------------

def test_a_control_connection_steps_the_world_and_sees_it_whole():
    with serve_world(MEADOW) as server:
        with WorldSession(server.url, control=True) as god, WorldSession(server.url, 'ana') as ana:
            ana.send('earn')
            god.act(ticks=2)
            world = god.peek()
            assert world['tick'] == ana.observe()['tick'] == 3
            assert world['entities']['hero:ana']['purse'] == 1 and world['players'] == {'ana': 'hero:ana'}
            assert ana.observe()['me']['purse'] == 1
            with pytest.raises(WorldSessionError, match='sends no commands'):
                god.act(send=[('earn', {})])


def test_a_live_world_has_no_control_connection():
    with serve_world(MEADOW, step=False) as server:
        with pytest.raises(WorldSessionError, match="a test world's"):
            WorldSession(server.url, control=True)


# --- the views read from the index are the views read from the world --------------------------------------------

class _Socket:
    def __init__(self):
        self.frames = []

    async def send(self, data):
        self.frames.append(json.loads(data))

    async def close(self):
        pass


def _brute(world, view, me, account):
    """A view read the slow way: every entity of the world, against where=."""
    return {eid: world.public(e, account) for eid, e in world.entities.items() if world.sees(view, e, me)}


def test_the_index_gives_what_reading_the_whole_world_gives():
    """Forty players walk, jump across the map, shout, hush, earn, leave and come back (half of them mostly
    standing), for a hundred and twenty ticks; after each, what each one was sent, applied, is what reading the world
    whole says it sees."""
    from quantum.runtime.gameserver.server import Connection

    definition = meadow()
    rng = random.Random(7)
    ways = ['north', 'south', 'east', 'west', 'northeast', 'southwest']

    async def run():
        server = WorldServer(definition, step=True, quiet=True, data_dir=Path('/nonexistent/never-written'))
        server.world = World(definition)
        names = [f'p{i}' for i in range(40)]
        sockets, have = {}, {}
        for name in names:
            sockets[name] = _Socket()
            server.connections[name] = Connection(sockets[name], name)
            server.inbox.append(('join', name))
            have[name] = {v: {} for v in definition.views}
        for tick in range(120):
            out = server.world.step(server.inbox)
            server.inbox = []
            await server._send(out)
            for name in names:
                for frame in sockets[name].frames:
                    if frame.get('type') == 'welcome':
                        have[name] = {v: {} for v in definition.views}
                    if frame.get('type') != 'tick':
                        continue
                    for v, change in frame.get('views', {}).items():
                        seen = have[name][v]
                        for e in change.get('enter', []):
                            assert e['id'] not in seen, (tick, name, v, e['id'])
                            seen[e['id']] = json.loads(json.dumps(e))
                        for u in change.get('update', []):
                            assert u['id'] in seen, (tick, name, v, u['id'])
                            seen[u['id']].update(u)
                        for eid in change.get('leave', []):
                            del seen[eid]
                sockets[name].frames = []
                if name in server.world.players:
                    me = server.world.entities[server.world.players[name]]
                    for v, view in definition.views.items():
                        assert have[name][v] == _brute(server.world, view, me, name), (tick, name, v)
            for name in names:
                roll = rng.random()
                if name not in server.connections:
                    if roll < 0.3:                  # back
                        server.connections[name] = Connection(sockets[name], name)
                        server.inbox.append(('join', name))
                    continue
                if int(name[1:]) >= 20 and rng.random() < 0.8:
                    continue                        # half of them mostly stand: what they see changes around them
                if roll < 0.55:
                    command = ('step', {'dir': rng.choice(ways)})
                elif roll < 0.65:
                    command = ('go', {'to': {'x': rng.randint(1, 46), 'y': rng.randint(1, 30)}})
                elif roll < 0.72:
                    command = ('shout', {'text': 'hi'})
                elif roll < 0.8:
                    command = ('hush', {})
                elif roll < 0.9:
                    command = ('earn', {})
                elif roll < 0.93:
                    del server.connections[name]
                    server.inbox.append(('leave', name))
                    continue
                else:
                    continue
                server.inbox.append(('cmd', name, tick, command[0], command[1]))
        # and the index holds every entity in the cell of its tile
        for eid, entity in server.world.entities.items():
            at = entity['at']
            assert server.world.cell_of[eid] == (at['x'] // CELL, at['y'] // CELL)
        assert sum(len(c) for c in server.world.cells.values()) == len(server.world.entities)

    asyncio.run(run())
