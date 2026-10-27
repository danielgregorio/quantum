"""A game's world, as its compiler reads it: what qg:connect's world= file says the game may ask and will see.

A game that is a world's client (PLAN_GAME_SERVER.md, Phase 2) holds none of the world's rules: they are the
server's. But the compiler reads the world's own file, so what the game says of it is checked as the game compiles,
not refused by the server as it runs: a qg:send of a command the world has not, or without its arguments; a
qg:mirror of a view it has not; a qg:on-event of an event it never emits; a field no entity of it has; a kind of
entity with no prefab to draw it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from quantum.runtime.godot.errors import GameCompileError

# what every entity of a world has, besides its fields (quantum/runtime/gameserver/world.py, World.make)
ENTITY_FIELDS = ('id', 'kind', 'at', 'facing')


@dataclass
class WorldInfo:
    path: Path
    name: str
    commands: Dict[str, List[str]]                     # a command: its params
    views: List[str]
    events: Set[str]
    kinds: Dict[str, float]                            # a kind of entity: the seconds a step of it takes
    fields: Set[str] = field(default_factory=set)      # every field of every entity, and id, kind, at, facing
    private: Set[str] = field(default_factory=set)     # the private ones: a player sees only its own entity's
    hero_kind: str = ''


def read_world(path: Path, line: Optional[int]) -> WorldInfo:
    """The world of a qg:connect world= file: its .server.q, read by the game server's own reader."""
    from quantum.runtime.gameserver import GameServerError
    from quantum.runtime.gameserver.model import Q_NS
    from quantum.runtime.gameserver.server import load

    try:
        world = load(str(path))
    except GameServerError as e:
        raise GameCompileError(f'<qg:connect world="{path.name}">: the world does not read: {e}', line) from None
    except SystemExit as e:
        raise GameCompileError(f'<qg:connect world="{path.name}">: {e}', line) from None
    events: Set[str] = set()
    blocks = ([c.body for c in world.commands.values()] + [b for _, b in world.every] + world.on_join
              + world.on_leave + [f.body for f in world.functions.values()])
    for block in blocks:
        for el in block.iter(f'{Q_NS}emit'):
            events.add(el.get('event'))
    kinds: Dict[str, float] = {}
    fields: Set[str] = set(ENTITY_FIELDS)
    private: Set[str] = set()
    for e in world.entities.values():
        kinds[e.kind] = round(e.step_ticks / world.tick_rate, 4)
        for f in e.fields:
            fields.add(f.name)
            if f.private:
                private.add(f.name)
    return WorldInfo(path, world.name, {c.name: list(c.params) for c in world.commands.values()},
                     list(world.views), events, kinds, fields, private, world.hero.kind)
