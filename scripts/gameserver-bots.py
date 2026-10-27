#!/usr/bin/env python3
"""A hundred bots walk a world, and the world's numbers are measured (PLAN_GAME_SERVER.md, Phase 2).

The world is made for the run: a field of SIZE by SIZE tiles walled round, a hero that walks four steps a second,
a view of the tiles within VIEW of it. The server runs in its own process at ten ticks a second (`quantum gameserver
run --stats`), so the bots do not take its time; the bots are one asyncio process, each walking a few steps one way
and then another, as a player does. What it says at the end is the server's own measure of its ticks (the median,
the 99th percentile, the worst) and of what it sent each player, and what the bots received.

    python scripts/gameserver-bots.py --bots 100 --seconds 3600          # an hour
    python scripts/gameserver-bots.py --bots 100 --seconds 60 --json numbers.json
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
import time
from pathlib import Path

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


def world_of(directory: Path, size: int, view: int, bots: int) -> Path:
    (directory / 'field.tmx').write_text(tmx_of(size, size))
    path = directory / 'field.server.q'
    path.write_text(f'''<q:application id="field-server" type="gameserver">
  <q:gameserver name="field" tick="10" players="{bots + 10}">
    <q:map name="field" tiled="field.tmx" />
    <q:entity name="hero" kind="Hero" per-player="true" speed="4/s">
      <q:field name="name" value="{{account.name}}" />
      <q:field name="steps" value="0" private="true" />
    </q:entity>
    <q:view name="around" where="{{near(it, me, {view})}}" />
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


async def bot(url: str, name: str, until: float, got: dict) -> None:
    from websockets.asyncio.client import connect

    rng = random.Random(name)
    async with connect(url, max_size=8 * 1024 * 1024) as ws:
        await ws.send(json.dumps({'type': 'hello', 'name': name}))
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
        reader.cancel()


async def bots(url: str, count: int, seconds: float) -> dict:
    got = {'bytes': 0, 'frames': 0, 'sent': 0, 'acks': 0, 'refused': 0}
    until = time.monotonic() + seconds
    await asyncio.gather(*(bot(url, f'bot-{i}', until, got) for i in range(count)))
    return got


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--bots', type=int, default=100)
    parser.add_argument('--seconds', type=float, default=60)
    parser.add_argument('--size', type=int, default=96, help='the field\'s side, in tiles')
    parser.add_argument('--view', type=int, default=9, help='how far a hero sees, in tiles')
    parser.add_argument('--json', help='write the numbers here too')
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as scratch:
        directory = Path(scratch)
        world = world_of(directory, args.size, args.view, args.bots)
        port = free_port()
        server = subprocess.Popen(
            [sys.executable, '-m', 'quantum.cli.runner', 'gameserver', 'run', str(world), '--port', str(port),
             '--data', str(directory / 'data'), '--stats', '10'],
            cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            env={**os.environ, 'PYTHONUNBUFFERED': '1'})
        lines = []
        try:
            for line in server.stdout:
                lines.append(line)
                if ' on ws://' in line:
                    break
            began = time.monotonic()
            got = asyncio.run(bots(f'ws://127.0.0.1:{port}', args.bots, args.seconds))
            took = time.monotonic() - began
        finally:
            server.terminate()
            rest, _ = server.communicate(timeout=60)
            lines += rest.splitlines(keepends=True)

    stats = [json.loads(m.group(1)) for m in (re.search(r'stats (\{.*\})', line) for line in lines) if m]
    full = [s for s in stats if s['players'] >= args.bots]
    if not full:
        print(''.join(lines[-20:]))
        print('the server said no numbers with every bot in')
        return 1
    numbers = {
        'bots': args.bots, 'seconds': round(took), 'field': args.size, 'view': args.view,
        'tick_ms_p50': round(statistics.median(s['tick_ms_p50'] for s in full), 2),
        'tick_ms_p99': round(max(s['tick_ms_p99'] for s in full), 2),
        'tick_ms_max': round(max(s['tick_ms_max'] for s in full), 2),
        'player_kb_s_p50': round(statistics.median(s['player_kb_s_p50'] for s in full), 2),
        'player_kb_s_max': round(max(s['player_kb_s_max'] for s in full), 2),
        'world_kb_s': round(statistics.median(s['out_kb_s'] for s in full), 1),
        'steps_sent': got['sent'], 'steps_ran': got['acks'], 'refused': got['refused'],
        'received_mb': round(got['bytes'] / 1e6, 1), 'frames': got['frames'],
    }
    print(json.dumps(numbers, indent=2))
    if args.json:
        Path(args.json).write_text(json.dumps({'numbers': numbers, 'stats': stats}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
