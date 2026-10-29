"""The load's gauge (PLAN_WORLD_ENGINE.md, E0): scripts/gameserver-bots.py, without running the bots.

Its field, with beasts that wander and chase, is a world the server reads; the beasts it asks for are there once the
world has ticked; the server's numbers say the beasts and the memory; a sweep's runs make the plan's table; the
server and the bots are given half the cores each on a machine of four or more.
"""

import argparse
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from quantum.core.parser import QuantumParser
from quantum.runtime.gameserver import World, read_world
from quantum.runtime.gameserver.server import WorldServer

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts' / 'gameserver-bots.py'


def bots():
    spec = spec_from_file_location('gameserver_bots', SCRIPT)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_field_holds_the_beasts_asked_for(tmp_path):
    script = bots()
    path = script.world_of(tmp_path, 40, 9, 5, beasts=60)
    definition = read_world(QuantumParser(use_cache=False).parse_file(str(path)), str(path))
    assert definition.map.areas['field'] == (1, 1, 38, 38) and 'beast' in definition.entities
    world = World(definition)
    world.step([('join', f'bot-{i}') for i in range(5)])
    beasts = [e for e in world.entities.values() if e['kind'] == 'Beast']
    assert len(beasts) == 60 and len({(b['at']['x'], b['at']['y']) for b in beasts}) == 60
    for _ in range(30):                                   # they live: the brains run, and none is in a wall
        world.step([])
    assert all(world.walkable((b['at']['x'], b['at']['y'])) for b in beasts)
    server = WorldServer(definition, quiet=True, data_dir=tmp_path / 'data')
    server.world = world
    numbers = server.stats()
    assert numbers['players'] == 5 and numbers['beasts'] == 60 and numbers['memory_mb'] > 0
    assert 'beast' not in script.world_of(tmp_path, 40, 9, 5).read_text()       # no beasts: the field as it was


def test_a_sweep_makes_the_plans_table():
    script = bots()
    runs = [{'bots': 100, 'beasts': 0, 'tick_ms_p50': 9.4, 'tick_ms_p99': 17.6, 'tick_ms_max': 216.0,
             'player_kb_s_p50': 1.16, 'memory_mb': 40, 'dropped': 0},
            {'bots': 500, 'beasts': 1500, 'tick_ms_p50': 91.2, 'tick_ms_p99': 176.8, 'tick_ms_max': 242.1,
             'player_kb_s_p50': 3.14, 'memory_mb': 120, 'dropped': 0},
            {'bots': 50, 'url': 'ws://elsewhere:7700', 'dropped': 1}]
    lines = script.table(runs).splitlines()
    assert lines[0].startswith('| Bots | Beasts | Tick, median | Tick, 99th percentile | Worst |')
    assert lines[2] == '| 100 | 0 | 9.4 ms | 17.6 ms | 216.0 ms | 1.16 KB/s | 40 MB | 0 |'
    assert lines[3] == '| 500 | 1500 | 91.2 ms | 176.8 ms | 242.1 ms | 3.14 KB/s | 120 MB | 0 |'
    assert lines[4].startswith('| 50 | | (a server elsewhere')


def test_the_server_and_the_bots_have_cores_of_their_own(monkeypatch):
    script = bots()
    monkeypatch.setattr(script.os, 'sched_getaffinity', lambda pid: {0, 1, 2, 3, 4, 5}, raising=False)
    assert script.cores_split() == ({0, 1, 2}, {3, 4, 5})
    monkeypatch.setattr(script.os, 'sched_getaffinity', lambda pid: {0, 1}, raising=False)
    assert script.cores_split() == (None, None)              # two cores: shared, as before


def test_bots_against_a_server_elsewhere_say_their_side_only(monkeypatch):
    script = bots()

    async def fake(url, count, seconds, tickets=None):
        assert url == 'ws://elsewhere:7700' and count == 3 and tickets is None
        return {'bytes': 2_000_000, 'frames': 90, 'sent': 30, 'acks': 28, 'refused': 2, 'dropped': 0}
    monkeypatch.setattr(script, 'bots', fake)
    args = argparse.Namespace(url='ws://elsewhere:7700', seconds=1.0)
    numbers = script.measure(args, 3)
    assert numbers == {'bots': 3, 'seconds': 1, 'url': 'ws://elsewhere:7700', 'steps_sent': 30, 'steps_ran': 28,
                       'refused': 2, 'dropped': 0, 'received_mb': 2.0, 'frames': 90}
