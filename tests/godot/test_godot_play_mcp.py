"""The play protocol, phase 4: the console (``quantum play``) and the MCP server.

The MCP server is driven here by a real MCP client, in memory: the same
tools a Claude Code session reaches through .mcp.json at the repository's
root. The console is driven by typed lines.
"""

import asyncio
import json
from pathlib import Path

import pytest

from quantum.cli.play import describe, run_play
from quantum.runtime.play_tools import PlayTools

REPO = Path(__file__).resolve().parents[2]


def test_the_console_plays_by_typed_words(godot):
    typed = iter(['right 16', 'tap select', 'until talking with down', 'snap', 'back', 'view',
                  'fly 3', 'quit'])
    out = []
    code = run_play('rpg', read=lambda _prompt: next(typed), write=out.append, tools=PlayTools(binary=godot))
    text = '\n'.join(out)
    assert code == 0
    assert 'tick 16 · exploration · player (4,4)' in text                       # one cell right
    assert 'stopped: max_ticks' in text and '×' in text                          # bumps told once, counted
    assert 's1:1' in text                                                       # the snapshot's name
    assert '#..@' in text or '#...' in text                                     # the view printed
    assert 'what is "fly 3"?' in text                                           # not an action of the game


def test_describe_says_where_what_happened_and_what_is_shown():
    obs = {'tick': 48, 'scene': 'combat', 'stopped': 'condition',
           'state': {'nodes': {}},
           'events': [{'kind': 'set', 'name': 'life', 'from': 10, 'to': 8, 'tick': 40},
                      {'kind': 'bump', 'who': 'player', 'tick': 41, 'times': 3, 'until': 45}],
           'screen': [{'kind': 'hud', 'items': ['Player', {'bar': 'life', 'value': 8, 'max': 10}]},
                      {'kind': 'menu', 'shown': True, 'focus': 1,
                       'items': [{'button': 'Attack'}, {'button': 'Defend'}, {'button': 'Potion', 'shown': False}]},
                      {'kind': 'dialogue', 'who': 'OPPONENT', 'text': 'Aha!'}]}
    assert describe(obs) == ['tick 48 · combat · stopped: condition',
                             '  [40] set name=life, from=10, to=8',
                             '  [41-45 ×3] bump who=player',
                             '  hud: Player | life 8/10',
                             '  menu: Attack  [Defend]',
                             '  "Aha!" — OPPONENT']


def test_repeated_events_are_told_once():
    events = [{'kind': 'bump', 'who': 'p', 'tick': t} for t in (1, 17, 33)] + [{'kind': 'step', 'who': 'p', 'tick': 49}]
    assert PlayTools.squeeze(events) == [{'kind': 'bump', 'who': 'p', 'tick': 1, 'times': 3, 'until': 33},
                                         {'kind': 'step', 'who': 'p', 'tick': 49}]


def test_a_countdown_is_one_set_from_its_first_value_to_its_last():
    events = []
    for t in range(1, 5):
        events += [{'kind': 'set', 'name': 'wait', 'from': 15 - t, 'to': 14 - t, 'tick': t},
                   {'kind': 'set', 'name': 'hurt', 'from': 30 - t, 'to': 29 - t, 'tick': t}]
    events += [{'kind': 'damage', 'who': 'player', 'tick': 5}, {'kind': 'set', 'name': 'wait', 'from': 10, 'to': 0, 'tick': 5}]
    turns = [{'kind': 'set', 'name': 'turn', 'from': 'player', 'to': 'opponent', 'tick': 6},
             {'kind': 'set', 'name': 'turn', 'from': 'opponent', 'to': 'player', 'tick': 7}]
    assert PlayTools.squeeze(turns) == turns                             # a text is told at each change
    assert PlayTools.squeeze(events) == [
        {'kind': 'set', 'name': 'wait', 'from': 14, 'to': 10, 'tick': 1, 'times': 4, 'until': 4},
        {'kind': 'set', 'name': 'hurt', 'from': 29, 'to': 25, 'tick': 1, 'times': 4, 'until': 4},
        {'kind': 'damage', 'who': 'player', 'tick': 5},                 # something else happened: told apart
        {'kind': 'set', 'name': 'wait', 'from': 10, 'to': 0, 'tick': 5}]


def test_the_repository_declares_the_server():
    servers = json.loads((REPO / '.mcp.json').read_text())['mcpServers']
    assert servers['quantum-play']['args'] == ['-m', 'quantum.runtime.play_mcp']


def test_an_agent_wins_the_rpg_through_the_mcp_tools(godot):
    """Phase 4's check, in the tests: the RPG won through the MCP tools alone."""
    pytest.importorskip('mcp')
    from mcp.client import Client
    from quantum.runtime.play_mcp import build_server

    tools = PlayTools(binary=godot)
    server = build_server(tools)

    async def play():
        async with Client(server) as client:
            async def call(name, **args):
                result = await client.call_tool(name, args)
                assert not result.is_error, result.content[0].text
                return json.loads(result.content[0].text)

            listed = {t.name for t in (await client.list_tools()).tools}
            assert listed == {'play_games', 'play_start', 'play_observe', 'play_act', 'play_until', 'play_view',
                              'play_map', 'play_frame', 'play_snapshot', 'play_restore', 'play_tape', 'play_end'}
            assert 'rpg' in {g['game'] for g in await call('play_games')}
            start = await call('play_start', game='rpg')
            sid = start['session']
            assert start['map']['cells'][7] == '###...............##' and 'right' in start['controls']
            await call('play_until', session=sid, condition=['player.row == 7'], hold=['down'])
            seen = await call('play_until', session=sid, condition=['talking'], hold=['right'])
            while seen['scene'] == 'exploration':
                seen = await call('play_act', session=sid, tap=['select'], ticks=2)
            calls = 4
            while seen['scene'] == 'combat':
                calls += 1
                if seen['state']['turn'] == 'player':
                    seen = await call('play_act', session=sid, tap=['select'], ticks=2)
                else:
                    seen = await call('play_until', session=sid, condition=["turn == 'player'", 'changed scene'],
                                      max_ticks=120)
            seen = await call('play_until', session=sid, condition=['talking'], max_ticks=30)
            said = [v for v in seen['screen'] if v['kind'] == 'dialogue'][0]
            assert said['text'] == 'Congratulations, you won!'
            bad = await client.call_tool('play_act', {'session': sid, 'hold': ['fly']})
            assert bad.is_error and 'no such action: fly' in bad.content[0].text
            await call('play_end', session=sid)
            return calls

    try:
        assert asyncio.run(play()) < 40
    finally:
        tools.close()
