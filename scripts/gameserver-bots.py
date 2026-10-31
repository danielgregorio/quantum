#!/usr/bin/env python3
"""Bots walk a world, and the world's numbers are measured (PLAN_GAME_SERVER.md, Phase 2; PLAN_WORLD_ENGINE.md, E0).

The world is made for the run: a field of SIZE by SIZE tiles walled round, a hero that walks four steps a second,
a view of the tiles within VIEW of it, and BEASTS that wander the field and chase a hero who comes near. Or it is a
world of its own (--world: Outpost, say; a world of a site's accounts gets a ticket for each bot). The server runs in
its own process at ten ticks a second (`quantum gameserver run --stats`), on its own cores when the machine has four
or more (the bots on the others), so the bots do not take its time; the bots are one asyncio process, each walking
a few steps one way and then another, as a player does. What it says at the end is the server's own measure of its
ticks (the median, the 99th percentile, the worst), of what it sent each player and of its memory, and what the bots
received. --sweep measures one count of bots after another and writes the table of PLAN_WORLD_ENGINE.md.

    python scripts/gameserver-bots.py --bots 100 --seconds 3600                 # an hour
    python scripts/gameserver-bots.py --bots 100 --seconds 60 --json numbers.json
    python scripts/gameserver-bots.py --sweep 100,200,500 --seconds 60          # the plan's table
    python scripts/gameserver-bots.py --bots 500 --beasts 1500 --seconds 600    # the plan's numbers
    python scripts/gameserver-bots.py --bots 200 --world projects/outpost/outpost.server.q
    python scripts/gameserver-bots.py --bots 200 --url ws://world.example:7700  # a server elsewhere: the bots alone
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
WAYS = ('north', 'south', 'east', 'west', 'northeast', 'northwest', 'southeast', 'southwest')


def tmx_of(width: int, height: int, walls=(), areas=None) -> str:
    """A Tiled map a world reads: a floor, a layer of walls (collision) round it and at `walls`, and its areas."""
    inner = set(walls)

    def wall(x: int, y: int) -> bool:
        return x in (0, width - 1) or y in (0, height - 1) or (x, y) in inner

    def csv(cell) -> str:
        return ',\n'.join(','.join(str(cell(x, y)) for x in range(width)) for y in range(height))

    objects = ''.join(
        f'  <object id="{i}" name="{name}" class="zone" x="{x0 * 16}" y="{y0 * 16}" width="{(x1 - x0 + 1) * 16}" '
        f'height="{(y1 - y0 + 1) * 16}">\n   <properties>\n    <property name="tag" value="area"/>\n   </properties>\n'
        f'  </object>\n' for i, (name, (x0, y0, x1, y1)) in enumerate(sorted((areas or {}).items()), start=1))
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<map version="1.10" tiledversion="1.10.2" orientation="orthogonal" renderorder="right-down" '
            f'width="{width}" height="{height}" tilewidth="16" tileheight="16" infinite="0" nextlayerid="4" '
            f'nextobjectid="{len(areas or {}) + 1}">\n'
            f' <tileset firstgid="1" name="field" tilewidth="16" tileheight="16" tilecount="4" columns="4">\n'
            f'  <image source="field.png" width="64" height="16"/>\n </tileset>\n'
            f' <layer id="1" name="floor" width="{width}" height="{height}">\n  <data encoding="csv">\n'
            f'{csv(lambda x, y: 1)}\n</data>\n </layer>\n'
            f' <layer id="2" name="walls" width="{width}" height="{height}">\n  <properties>\n'
            f'   <property name="collision" type="bool" value="true"/>\n  </properties>\n  <data encoding="csv">\n'
            f'{csv(lambda x, y: 2 if wall(x, y) else 0)}\n</data>\n </layer>\n'
            f' <objectgroup id="3" name="areas">\n{objects} </objectgroup>\n</map>\n')


def world_of(directory: Path, size: int, view: int, bots: int, beasts: int = 0) -> Path:
    (directory / 'field.tmx').write_text(tmx_of(size, size, areas={'field': (1, 1, size - 2, size - 2)}))
    path = directory / 'field.server.q'
    beast = f'''    <q:entity name="beast" kind="Beast" speed="2/s">
      <q:brain>
        <q:state name="roam" initial="true" do="wander" within="3">
          <q:when condition="{{nearest(it, 'Hero', 3) != null}}" become="chase" />
        </q:state>
        <q:state name="chase" do="chase" target="{{nearest(it, 'Hero', 6)}}">
          <q:when condition="{{it.target == ''}}" become="roam" />
        </q:state>
      </q:brain>
    </q:entity>
    <q:spawn entity="beast" area="field" count="{beasts}" respawn="30s" />
''' if beasts else ''
    path.write_text(f'''<q:application id="field-server" type="gameserver">
  <q:gameserver name="field" tick="10" players="{bots + 10}">
    <q:map name="field" tiled="field.tmx" />
    <q:entity name="hero" kind="Hero" per-player="true" speed="4/s">
      <q:field name="name" value="{{account.name}}" />
      <q:field name="steps" value="0" private="true" />
    </q:entity>
{beast}    <q:view name="around" where="{{near(it, me, {view})}}" />
    <q:command name="step" params="dir" limit="8/s">
      <q:require condition="{{walkable(ahead(me, dir))}}" else="A wall." />
      <q:move entity="{{me}}" to="{{ahead(me, dir)}}" />
      <q:set name="me.steps" value="{{me.steps + 1}}" />
    </q:command>
    <q:on-join>
      <q:if condition="{{me.at == null}}">
        <q:move entity="{{me}}" to="{{ {{'x': random(1, {size - 2}), 'y': random(1, {size - 2})}} }}" />
      </q:if>
    </q:on-join>
  </q:gameserver>
</q:application>
''')
    return path


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


async def bot(url: str, name: str, until: float, got: dict, ticket: str = '') -> None:
    from websockets.exceptions import ConnectionClosed

    try:
        await _walk(url, name, until, got, ticket)
    except (ConnectionClosed, OSError):
        got['dropped'] += 1                  # counted, and the others go on: a measure is not lost to one


async def _walk(url: str, name: str, until: float, got: dict, ticket: str = '') -> None:
    from websockets.asyncio.client import connect

    rng = random.Random(name)
    async with connect(url, max_size=8 * 1024 * 1024) as ws:
        await ws.send(json.dumps({'type': 'hello', 'ticket': ticket} if ticket else {'type': 'hello', 'name': name}))
        seq, way, left = 0, rng.choice(WAYS), 0

        async def read() -> None:
            async for raw in ws:
                got['bytes'] += len(raw)
                got['frames'] += 1
                message = json.loads(raw)
                if message.get('type') == 'tick':
                    got['refused'] += len(message.get('refused', []))
                    got['acks'] += len(message.get('ack', []))

        reader = asyncio.create_task(read())
        await asyncio.sleep(rng.random())
        while time.monotonic() < until and not reader.done():
            if left <= 0:
                way, left = rng.choice(WAYS), rng.randint(2, 12)
            seq += 1
            left -= 1
            await ws.send(json.dumps({'type': 'cmd', 'seq': seq, 'name': 'step', 'args': {'dir': way}}))
            got['sent'] += 1
            await asyncio.sleep(0.3 + rng.random() * 0.05)          # four steps a second, as the hero walks
        if reader.done() and reader.exception() is not None:
            raise reader.exception()
        reader.cancel()


async def bots(url: str, count: int, seconds: float, tickets: Optional[Dict[str, str]] = None) -> dict:
    got = {'bytes': 0, 'frames': 0, 'sent': 0, 'acks': 0, 'refused': 0, 'dropped': 0}
    until = time.monotonic() + seconds
    await asyncio.gather(*(bot(url, f'bot-{i}', until, got, (tickets or {}).get(f'bot-{i}', ''))
                           for i in range(count)))
    return got


def cores_split() -> Tuple[Optional[set], Optional[set]]:
    """The server's cores and the bots': half and half, on a machine of four or more; else (None, None), all for both."""
    try:
        cores = sorted(os.sched_getaffinity(0))
    except AttributeError:                    # not Linux: no affinity to set
        return None, None
    if len(cores) < 4:
        return None, None
    half = len(cores) // 2
    return set(cores[:half]), set(cores[half:])


def measure(args, count: int) -> dict:
    """One run: a server (unless --url), `count` bots for --seconds, the numbers."""
    if args.url:
        got = asyncio.run(bots(args.url, count, args.seconds))
        return {'bots': count, 'seconds': round(args.seconds), 'url': args.url, **_bots_side(got)}
    server_cores, bot_cores = (None, None) if args.no_split else cores_split()
    with tempfile.TemporaryDirectory() as scratch:
        directory = Path(scratch)
        env = {**os.environ, 'PYTHONUNBUFFERED': '1'}
        tickets_for = None
        if args.world:
            world = Path(args.world).resolve()
            if 'accounts="site"' in world.read_text(encoding='utf-8'):
                from quantum.runtime.gameserver import tickets
                secret = os.urandom(24).hex()
                env[tickets.SECRET_ENV] = secret
                tickets_for = {f'bot-{i}': tickets.issue(f'bot-{i}', f'Bot {i}', secret.encode(),
                                                         seconds=args.seconds + 120) for i in range(count)}
        else:
            world = world_of(directory, args.size, args.view, count, args.beasts)
        port = free_port()

        def pin() -> None:
            if server_cores:
                os.sched_setaffinity(0, server_cores)
        server = subprocess.Popen(
            [sys.executable, '-m', 'quantum.cli.runner', 'gameserver', 'run', str(world), '--port', str(port),
             '--data', str(directory / 'data'), '--stats', '10', '--no-minds', '--engine', args.engine],
            cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env,
            preexec_fn=pin if server_cores else None)
        if bot_cores:
            os.sched_setaffinity(0, bot_cores)
        lines = []
        listening = threading.Event()

        def drain() -> None:              # read all the server says: a pipe left full would stop its loop
            for line in server.stdout:
                lines.append(line)
                if ' on ws://' in line:
                    listening.set()
            listening.set()

        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        try:
            listening.wait(60)
            began = time.monotonic()
            got = asyncio.run(bots(f'ws://127.0.0.1:{port}', count, args.seconds, tickets_for))
            took = time.monotonic() - began
        finally:
            server.terminate()
            server.wait(timeout=60)
            reader.join(10)

    stats = [json.loads(m.group(1)) for m in (re.search(r'stats (\{.*\})', line) for line in lines) if m]
    full = [s for s in stats if s['players'] >= count]
    if not full:
        print(''.join(lines[-20:]))
        raise SystemExit(f'the server said no numbers with every one of the {count} bots in')
    if len(full) > 1:
        full = full[1:]                  # the first holds the bots coming in and the beasts being made: not the world
    return {
        'bots': count, 'seconds': round(took), 'world': world.name if args.world else 'field', 'field': args.size,
        'view': args.view, 'beasts': round(statistics.median(s.get('beasts', 0) for s in full)),
        'server_cores': len(server_cores) if server_cores else None,
        'bot_cores': len(bot_cores) if bot_cores else None,
        'tick_ms_p50': round(statistics.median(s['tick_ms_p50'] for s in full), 2),
        'tick_ms_p99': round(statistics.median(s['tick_ms_p99'] for s in full), 2),    # of an interval, typically
        'tick_ms_max': round(max(s['tick_ms_max'] for s in full), 2),                  # the worst tick of all
        'engine': args.engine,
        'step_ms_p50': round(statistics.median(s.get('step_ms_p50', 0) for s in full), 2),         # the rules
        'send_ms_p50': round(statistics.median(s.get('send_ms_p50', 0) for s in full), 2),         # views, sending
        'send_ms_p99': round(statistics.median(s.get('send_ms_p99', 0) for s in full), 2),
        'intervals_over_50ms': sum(1 for s in full if s['tick_ms_max'] > 50), 'intervals': len(full),
        'player_kb_s_p50': round(statistics.median(s['player_kb_s_p50'] for s in full), 2),
        'player_kb_s_max': round(max(s['player_kb_s_max'] for s in full), 2),
        'world_kb_s': round(statistics.median(s['out_kb_s'] for s in full), 1),
        'memory_mb': round(max(s.get('memory_mb', 0) for s in full)),
        **_bots_side(got), 'stats': stats,
    }


def _bots_side(got: dict) -> dict:
    return {'steps_sent': got['sent'], 'steps_ran': got['acks'], 'refused': got['refused'], 'dropped': got['dropped'],
            'received_mb': round(got['bytes'] / 1e6, 1), 'frames': got['frames']}


def table(runs: List[dict]) -> str:
    """The runs as the table of PLAN_WORLD_ENGINE.md."""
    rows = ['| Engine | Bots | Beasts | Tick, median | Tick, 99th percentile | Worst | The rules, median | '
            'Views and sending, median | Each player receives | Memory | Dropped |',
            '|---|---|---|---|---|---|---|---|---|---|---|']
    for r in runs:
        if 'tick_ms_p50' not in r:
            rows.append(f"| | {r['bots']} | | (a server elsewhere: its own numbers) | | | | | | | {r['dropped']} |")
            continue
        rows.append(f"| {r.get('engine', 'python')} | {r['bots']} | {r['beasts']} | {r['tick_ms_p50']} ms | "
                    f"{r['tick_ms_p99']} ms | {r['tick_ms_max']} ms | {r.get('step_ms_p50', 0)} ms | "
                    f"{r.get('send_ms_p50', 0)} ms | {r['player_kb_s_p50']} KB/s | {r['memory_mb']} MB | "
                    f"{r['dropped']} |")
    return '\n'.join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--bots', type=int, default=100)
    parser.add_argument('--sweep', help='several counts of bots, one run each, and the table of them: 100,200,500')
    parser.add_argument('--seconds', type=float, default=60)
    parser.add_argument('--size', type=int, default=96, help='the field\'s side, in tiles')
    parser.add_argument('--view', type=int, default=9, help='how far a hero sees, in tiles')
    parser.add_argument('--beasts', type=int, default=0, help='beasts that wander the field and chase a hero near')
    parser.add_argument('--world', help='a world of its own to walk in, in place of the field (its command `step`)')
    parser.add_argument('--url', help='a server already running elsewhere: the bots alone, against it')
    parser.add_argument('--no-split', action='store_true',
                        help='the server and the bots on every core (else half each, on four cores or more)')
    parser.add_argument('--engine', choices=('python', 'rust', 'native'), default='python',
                        help='what runs the world (PLAN_WORLD_ENGINE.md): python; rust (native/world: the views and '
                             'the network); or native (the world itself too, E3)')
    parser.add_argument('--json', help='write the numbers here too')
    args = parser.parse_args()

    counts = [int(c) for c in args.sweep.split(',')] if args.sweep else [args.bots]
    runs = []
    for count in counts:
        numbers = measure(args, count)
        runs.append(numbers)
        print(json.dumps({k: v for k, v in numbers.items() if k != 'stats'}, indent=2), flush=True)
    if len(runs) > 1 or args.sweep:
        print(table(runs))
    if args.json:
        Path(args.json).write_text(json.dumps({'runs': runs, 'table': table(runs)} if args.sweep else
                                              {'numbers': {k: v for k, v in runs[0].items() if k != 'stats'},
                                               'stats': runs[0].get('stats', [])}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
