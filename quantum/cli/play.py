"""``quantum play``: a game played a request at a time, in the terminal.

    quantum play rpg                 # a game of projects/, or a .q
    quantum play --mcp               # the same tools, as an MCP server over stdio

The console is the play protocol for a person: what an agent sends as
requests, typed as words, and what it gets back, printed short. It is how
someone checks what an agent sees, and a way to poke at a game while making
it.

    right 32          hold "right" for 32 ticks (16 when not given)
    tap select        press "select" for one tick
    until talking with right     hold "right" until someone talks ("until event:say", ...)
    look | view | map            the observation, the screen as text, the scene's tiles
    snap | back [name]           mark this point; come back to it (the last one by default)
    tape won.json | frame shot.png | help | quit
"""

from __future__ import annotations

import shlex
from typing import Callable, List, Optional

from quantum.runtime.godot_play import PlayError
from quantum.runtime.play_tools import PlayTools

HELP = __doc__.split('\n\n', 3)[3].rstrip()


def describe(obs: dict) -> List[str]:
    """An observation in a few lines: where, what happened, what the screen says."""
    lines = []
    state = obs.get('state', {})
    nodes = state.get('nodes', {})
    where = '  '.join(f'{name} ({n["col"]},{n["row"]})' if 'col' in n else f'{name} ({n["x"]:.0f},{n["y"]:.0f})'
                      for name, n in nodes.items())
    head = f'tick {obs.get("tick")} · {obs.get("scene")}'
    if obs.get('stopped') and obs['stopped'] not in ('ticks',):
        head += f' · stopped: {obs["stopped"]}'
    lines.append(head + (f' · {where}' if where else ''))
    for e in obs.get('events', []):
        rest = ', '.join(f'{k}={v}' for k, v in e.items() if k not in ('kind', 'tick', 'times', 'until'))
        when = f'{e["tick"]}-{e["until"]} ×{e["times"]}' if e.get('times') else str(e['tick'])
        lines.append(f'  [{when}] {e["kind"]}' + (f' {rest}' if rest else ''))
    for v in obs.get('screen', []):
        if v.get('kind') == 'hud':
            texts = [i if isinstance(i, str) else f'{i["bar"]} {i["value"]:g}/{i["max"]:g}' for i in v['items']]
            lines.append('  hud: ' + ' | '.join(texts))
        elif v.get('kind') == 'dialogue':
            lines.append(f'  "{v["text"]}" — {v["who"]}' if v.get('who') else f'  "{v["text"]}"')
        elif v.get('kind') == 'menu' and v.get('shown'):
            items = []
            for i, item in enumerate(v['items']):
                if not item.get('shown', True):
                    continue
                label = item.get('button') or f'{item.get("field")}: {item.get("value")}'
                items.append(f'[{label}]' if i == v['focus'] else label)
            lines.append('  menu: ' + '  '.join(items))
    return lines


def run_play(game: str, frames: bool = False, read: Callable[[str], str] = input,
             write: Callable[[str], None] = print, tools: Optional[PlayTools] = None) -> int:
    tools = tools or PlayTools()
    try:
        start = tools.start(game, frames=frames)
    except PlayError as e:
        write(f'[ERROR] {e}')
        return 1
    sid = start['session']
    actions = start['controls']
    write(f'{game}: {", ".join(actions)} — "help" for the commands')
    for line in describe(start):
        write(line)
    snaps: List[str] = []
    try:
        while True:
            try:
                text = read('> ').strip()
            except EOFError:
                break
            if not text:
                continue
            words = shlex.split(text)
            cmd, args = words[0], words[1:]
            try:
                if cmd in ('quit', 'exit', 'q'):
                    break
                elif cmd == 'help':
                    write(HELP)
                    continue
                elif cmd == 'look':
                    obs = tools.observe(sid)
                elif cmd == 'view':
                    v = tools.view(sid)
                    for row in v['view']:
                        write('  ' + row)
                    write('  ' + '  '.join(f'{k} {"/".join(n)}' for k, n in v['legend'].items()))
                    continue
                elif cmd == 'map':
                    m = tools.map(sid)
                    for row in (m or {}).get('cells', ['(no tiles in this scene)']):
                        write('  ' + row)
                    continue
                elif cmd == 'tap' and args:
                    obs = tools.act(sid, tap=args, ticks=2)
                elif cmd == 'until' and args:
                    held = []
                    if 'with' in args:
                        i = args.index('with')
                        args, held = args[:i], args[i + 1:]
                    obs = tools.until(sid, ' '.join(args), hold=held)
                elif cmd == 'snap':
                    snaps.append(tools.snapshot(sid)['snapshot'])
                    write(f'  {snaps[-1]}')
                    continue
                elif cmd == 'back':
                    name = args[0] if args else (snaps[-1] if snaps else '')
                    obs = tools.restore(sid, name)
                elif cmd == 'tape' and args:
                    write(f'  {tools.tape(sid, args[0])}')
                    continue
                elif cmd == 'frame':
                    write(f'  {tools.frame(sid, args[0] if args else None)["frame"]}')
                    continue
                elif cmd in actions:
                    obs = tools.act(sid, hold=[cmd], ticks=int(args[0]) if args else 16)
                else:
                    write(f'  what is "{text}"? "help" for the commands')
                    continue
            except (PlayError, ValueError) as e:
                write(f'  [ERROR] {e}')
                continue
            for line in describe(obs):
                write(line)
    finally:
        tools.close()
    return 0


def main(args) -> int:
    if args.mcp:
        from quantum.runtime.play_mcp import main as mcp_main
        return mcp_main()
    if not args.game:
        tools = PlayTools()
        print('quantum play <game>: ' + ', '.join(g['game'] for g in tools.games()))
        return 2
    return run_play(args.game, frames=args.frames)
