"""What each player is told of a tick: their welcome, their acks and refusals, what changed in each of their views,
their events. A function of the world after its tick and of what each player was told before: no socket, no clock.

The server sends these frames; the conformance harness (conform.py) makes them for each engine and compares them, so
two engines that agree on the frames agree on everything a player can see. A view is read again whole when the
player's entity changed (it moved, say); else only for what changed near it: the world's index of cells (16 tiles a
side) is how a view near a player reads only the entities around them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set

from quantum.runtime.gameserver.model import WorldDef
from quantum.runtime.gameserver.rules import chebyshev

_MISSING = object()


@dataclass
class Seen:
    """What a player has been told: whether they were welcomed, and what they have of each view, by id. The server's
    connection is one (it has these two, and more); the conformance harness keeps one for each player."""
    account: Optional[str]
    joined: bool = False
    views: Dict[str, Set[str]] = field(default_factory=dict)


def copy_value(value: Any) -> Any:
    """A world's value (numbers, texts, lists and records), copied: what was sent stays as it was sent."""
    if isinstance(value, dict):
        return {k: copy_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [copy_value(v) for v in value]
    return value


def _changed(before: dict, now: dict) -> dict:
    return {k: v for k, v in now.items() if before.get(k, _MISSING) != v}


class Frames:
    def __init__(self, definition: WorldDef):
        self.definition = definition
        self._public: Dict[str, dict] = {}                  # each entity as the players have it (as of the last tick)
        self._own: Dict[str, dict] = {}                     # a player's entity as its player has it

    def welcome(self, world, account: str, tick: int) -> dict:
        return {'type': 'welcome', 'you': world.players[account], 'tick': tick, 'rate': self.definition.tick_rate,
                'world': self.definition.name, 'client': self.definition.client,
                'map': self.definition.map.path.name, 'views': list(self.definition.views)}

    def tick(self, world, out, seen: Dict[str, Any], welcoming: Iterable[str] = (),
             every_tick: bool = False) -> Dict[str, List[dict]]:
        """Each player's messages of the tick, in order: a welcome when they came in (or took their hero over), then
        the tick's frame, when it says something (every tick, with every_tick: a test world's harness waits for it).
        `seen` is what each player was told, by account (a full world's newcomers left out); it is updated."""
        welcoming = set(welcoming)
        theirs, mine = self._changes(world)
        dirty_cells: Dict[tuple, List[str]] = {}
        for eid in world.dirty:
            cell = world.cell_of.get(eid)
            if cell is not None:
                dirty_cells.setdefault(cell, []).append(eid)
        events = self._events(world, seen) if world.events else {}
        messages: Dict[str, List[dict]] = {}
        for account, player in seen.items():
            said: List[dict] = []
            if account in out.joined or (account in welcoming and account in world.players):
                player.joined = True
                player.views = {}
                said.append(self.welcome(world, account, out.tick))
            if player.joined and account in world.players:
                frame: Dict[str, Any] = {'type': 'tick', 'tick': out.tick}
                if out.acks.get(account):
                    frame['ack'] = out.acks[account]
                if out.refused.get(account):
                    frame['refused'] = out.refused[account]
                views = self._view(world, player, world.entities[world.players[account]], dirty_cells, theirs, mine)
                if views:
                    frame['views'] = views
                if events.get(account):
                    frame['events'] = events[account]
                if len(frame) > 2 or every_tick:
                    said.append(frame)
            if said:
                messages[account] = said
        for eid in world.gone:
            self._public.pop(eid, None)
            self._own.pop(eid, None)
        return messages

    def _changes(self, world) -> tuple:
        """What changed of each entity this tick, once for every player: (to the others, to its own player). An
        entity no player has yet has nothing to change."""
        theirs, mine = {}, {}
        for eid in world.dirty:
            entity = world.entities.get(eid)
            if entity is None:
                continue
            now = copy_value(world.public(entity, None))
            before = self._public.get(eid)
            if before is not None:
                changed = _changed(before, now)
                if changed:
                    theirs[eid] = {'id': eid, **changed}
                self._public[eid] = now
            owner = entity.get('_player')
            if owner is not None:
                now = copy_value(world.public(entity, owner))
                before = self._own.get(eid)
                if before is not None:
                    changed = _changed(before, now)
                    if changed:
                        mine[eid] = {'id': eid, **changed}
                    self._own[eid] = now
        return theirs, mine

    def _entering(self, world, entity: dict, account: str) -> dict:
        """An entity as it comes into a player's view: kept as they have it, for the changes of the ticks after."""
        eid = entity['id']
        if entity.get('_player') == account:
            if eid not in self._own:
                self._own[eid] = copy_value(world.public(entity, account))
            return self._own[eid]
        if eid not in self._public:
            self._public[eid] = copy_value(world.public(entity, None))
        return self._public[eid]

    def _view(self, world, player, me: dict, dirty_cells: Dict[tuple, List[str]], theirs: dict,
              mine: dict) -> Dict[str, dict]:
        """What of each view changed for this player: the ones that came in, the fields that changed, the ones that
        left."""
        me_changed = me['id'] in world.dirty
        out = {}
        for view in self.definition.views.values():
            had = player.views.get(view.name)
            if (had is None or me_changed or
                    (world.vars_changed and view.where is not None and (view.rest or view.radius is None))):
                members = world.members(view, me)
            else:
                members = had - world.gone
                if view.radius is not None:
                    tile = world.tile_of(me)
                    candidates = [eid for eid in had if eid in world.dirty]
                    if tile is not None:
                        for cell in world.cells_near(tile, view.radius):
                            candidates.extend(dirty_cells.get(cell, ()))
                else:
                    candidates = world.dirty
                for eid in candidates:
                    entity = world.entities.get(eid)
                    if entity is not None and world.sees(view, entity, me):
                        members.add(eid)
                    else:
                        members.discard(eid)
            had = had or set()
            frame = {}
            enter = sorted(members - had)
            if enter:
                frame['enter'] = [self._entering(world, world.entities[eid], player.account) for eid in enter]
            update = [(mine if eid == me['id'] else theirs).get(eid) for eid in sorted(members & had)
                      if eid in world.dirty]
            update = [u for u in update if u]
            if update:
                frame['update'] = update
            leave = sorted(had - members)
            if leave:
                frame['leave'] = leave
            if frame:
                out[view.name] = frame
            player.views[view.name] = members
        return out

    def _events(self, world, seen: Dict[str, Any]) -> Dict[str, List[dict]]:
        """Each player's events of the tick: theirs (to=), everyone's, and those where they see (at=)."""
        reach = self.definition.reach
        accounts = [a for a, p in seen.items() if p.joined and a in world.players]
        out: Dict[str, List[dict]] = {}
        for event in world.events:
            if event.accounts is not None:
                to = [a for a in event.accounts if a in seen]
            elif event.to is not None:
                to = [event.to] if event.to in seen else []
            elif event.everyone or (event.tile is not None and reach is None):
                to = accounts
            elif event.tile is None:
                to = []
            else:
                to = []
                for eid in world.near_ids(event.tile, reach):
                    entity = world.entities[eid]
                    owner = entity.get('_player')
                    if (owner is not None and owner in seen and world.players.get(owner) == eid
                            and chebyshev(world.tile_of(entity), event.tile) <= reach):
                        to.append(owner)
            for account in to:
                out.setdefault(account, []).append(event.message)
        return out
