"""The play protocol as an MCP server (PLAN_PLAY_PROTOCOL.md, phase 4).

    quantum play --mcp            # over stdio, as .mcp.json at the repository's root declares it

An agent connected to it plays the games of ``projects/`` through tools:
``play_games``, ``play_start``, ``play_observe``, ``play_act``, ``play_until``,
``play_view``, ``play_map``, ``play_frame``, ``play_snapshot``, ``play_restore``,
``play_tape`` and ``play_end``. Each answers in JSON. The game stands still
between calls, so the agent plays at its own pace. Needs the ``mcp`` package
(``pip install quantum[play]``).
"""

from __future__ import annotations

import json
from typing import List, Optional

from quantum.runtime.play_tools import PlayTools

INSTRUCTIONS = """Play the Quantum games of this repository, step by step.

play_games lists them. play_start opens one and answers a session id, the game's actions, the first
observation and the scene's map (# stops, - one-way, . open). The game stands still between calls.
play_act presses actions (hold: for all its ticks; tap: one tick; press/release: until changed) and runs
`ticks` ticks (60 a second). play_until does the same until a condition holds, which saves many calls:
"talking", "player.row == 7", "scene == 'combat'", "changed scene", "event:say", "event:touch with=key";
a list means any of them. Every answer says what happened in `events` (touch, hit, step, bump, spawn,
destroy, damage, sound, scene, say, choose, set: a variable that changed) and what the screen shows in
`screen` (the HUD's texts, the menus' buttons and focus, the dialogue's line). play_view draws the
screen as text. play_snapshot and play_restore try a choice and come back. play_tape saves the session
as a replay test. Close what you open with play_end."""


def _dump(value) -> str:
    return json.dumps(value, separators=(',', ':'))


def _plays(fn):
    """A tool whose refusals (an unknown action, a closed session...) reach the agent as their
    message: the server reports only a ToolError's own words."""
    import functools
    from mcp.server.mcpserver.exceptions import ToolError

    from quantum.runtime.godot_play import PlayError

    @functools.wraps(fn)
    def tool(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except PlayError as e:
            raise ToolError(str(e)) from e
    return tool


def build_server(tools: Optional[PlayTools] = None):
    """The MCP server, its tools bound to ``tools`` (a fresh ``PlayTools`` by default)."""
    from mcp.server.mcpserver import MCPServer

    tools = tools or PlayTools()
    server = MCPServer('quantum-play', instructions=INSTRUCTIONS)

    @server.tool()
    @_plays
    def play_games() -> str:
        """The games that can be played: name, title, how many play, what it is, its keys."""
        return _dump(tools.games())

    @server.tool()
    @_plays
    def play_start(game: str) -> str:
        """Opens a game by name (from play_games). Answers the session id, the game's actions,
        the first observation and the scene's map."""
        return _dump(tools.start(game))

    @server.tool()
    @_plays
    def play_observe(session: str) -> str:
        """What the game shows now, without running it."""
        return _dump(tools.observe(session))

    @server.tool()
    @_plays
    def play_act(session: str, ticks: int = 16, hold: Optional[List[str]] = None,
                 tap: Optional[List[str]] = None, press: Optional[List[str]] = None,
                 release: Optional[List[str]] = None, cursor: Optional[List[float]] = None) -> str:
        """Applies actions and runs `ticks` ticks (60 a second). hold: pressed for these ticks;
        tap: pressed one tick; press/release: held across calls until released; cursor: [x, y]
        where the player's pointer is (menus, boards)."""
        return _dump(tools.act(session, hold=hold or [], tap=tap or [], press=press or [],
                               release=release or [], cursor=cursor, ticks=ticks))

    @server.tool()
    @_plays
    def play_until(session: str, condition: List[str], max_ticks: int = 600,
                   hold: Optional[List[str]] = None, tap: Optional[List[str]] = None,
                   press: Optional[List[str]] = None, release: Optional[List[str]] = None,
                   cursor: Optional[List[float]] = None) -> str:
        """As play_act, but runs until any of the conditions holds or max_ticks have run.
        Conditions: "talking", "player.col == 11", "scene == 'combat'", "changed scene",
        "not paused", "event:say", "event:touch with=key". The answer's `stopped` says which."""
        cond = condition[0] if len(condition) == 1 else condition
        return _dump(tools.until(session, cond, hold=hold or [], tap=tap or [], press=press or [],
                                 release=release or [], cursor=cursor, max_ticks=max_ticks))

    @server.tool()
    @_plays
    def play_view(session: str) -> str:
        """The screen drawn as text, a character a map cell, with a legend of the letters."""
        return _dump(tools.view(session))

    @server.tool()
    @_plays
    def play_map(session: str) -> str:
        """The scene's tilemap: # stops, - one-way, . open (null for a scene without one)."""
        return _dump(tools.map(session))

    @server.tool()
    @_plays
    def play_frame(session: str, path: Optional[str] = None) -> str:
        """Saves the picture on the screen as a PNG and answers its path (a session started
        with a display only)."""
        return _dump(tools.frame(session, path))

    @server.tool()
    @_plays
    def play_snapshot(session: str) -> str:
        """Marks this point of the game; play_restore comes back to it."""
        return _dump(tools.snapshot(session))

    @server.tool()
    @_plays
    def play_restore(session: str, snapshot: str) -> str:
        """Back to a snapshot of this session, exactly as it was."""
        return _dump(tools.restore(session, snapshot))

    @server.tool()
    @_plays
    def play_tape(session: str, path: str) -> str:
        """Saves the session's inputs as a replay tape (JSON): the same game, as a test."""
        return _dump(tools.tape(session, path))

    @server.tool()
    @_plays
    def play_end(session: str) -> str:
        """Closes a game."""
        return _dump(tools.end(session))

    return server


def main() -> int:
    try:
        server = build_server()
    except ImportError:
        print('quantum play --mcp needs the mcp package: pip install "quantum[play]"')
        return 1
    server.run('stdio')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
