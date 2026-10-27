"""What a world does by itself (PLAN_GAME_SERVER.md, Phase 3): the entities its q:spawns keep, what their brains do a
tick at a time, the way of a q:travel, an entity's end (q:kill and the q:on-death of its kind) and what it leaves
(q:loot).

All of it runs inside the tick, on the world's state and its seeded random, in the order of the entities' ids, so a
replay is the same world. A brain runs only for an entity with a hero within AWAKE tiles: a region no one is in
sleeps, and costs nothing. A brain's tick is a transaction, as a command is: an expression of it that fails undoes
that entity's tick and is kept in the world's errors.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Callable, Dict, List, Optional, Tuple

from quantum.runtime.gameserver.errors import Refused, RuleError

AWAKE = 32               # tiles from a hero within which a brain runs
CHASE_SEARCH = 12        # how far a chase looks for its way
TRAVEL_SEARCH = 40       # how far a q:travel looks for its way
WANDER_CHANCE = 0.3      # a wanderer at rest steps with this chance a tick
# the eight ways, in the order a way is looked for (straight ones first: a way of as few diagonals as it needs)
STEPS: Tuple[Tuple[int, int], ...] = ((0, -1), (1, 0), (0, 1), (-1, 0), (1, -1), (1, 1), (-1, 1), (-1, -1))

Tile = Tuple[int, int]
MISSING = object()       # what a key held before a transaction set it, if nothing; World.put's value that takes it out


def _far(a: Tile, b: Tile) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


class Life:
    """Mixed into World: it reads and writes the world through World's own methods (write, put, move, reindex)."""

    # -- the clock ---------------------------------------------------------------------------------------------

    def daytime(self) -> float:
        """How far into its day the world is, 0 to 1 (0 with no q:clock)."""
        day = self.definition.day_ticks
        return (self.tick % day) / day if day else 0.0

    def is_night(self) -> bool:
        return bool(self.definition.day_ticks) and self.daytime() >= 1 - self.definition.night

    # -- tiles and ways ----------------------------------------------------------------------------------------

    def occupied(self, tile: Tile, but: Optional[str] = None) -> bool:
        for eid in self.near_ids(tile, 0):
            if eid != but and self.tile_of(self.entities[eid]) == tile:
                return True
        return False

    def free(self, tile: Tile, but: Optional[str] = None) -> bool:
        return self.walkable(tile) and not self.occupied(tile, but)

    def way(self, start: Tile, arrived: Callable[[Tile], bool], limit: int, but: Optional[str],
            through: bool = False) -> Optional[List[Tile]]:
        """The shortest way from start to a tile where arrived holds, within limit tiles of start, around walls (and
        around entities, unless through): its tiles after start; [] if start is one; None if there is none."""
        if arrived(start):
            return []
        came: Dict[Tile, Optional[Tile]] = {start: None}
        queue = deque([start])
        while queue:
            here = queue.popleft()
            for dx, dy in STEPS:
                there = (here[0] + dx, here[1] + dy)
                if there in came or _far(there, start) > limit or not self.walkable(there):
                    continue
                if not through and self.occupied(there, but) and not arrived(there):
                    continue
                came[there] = here
                if arrived(there):
                    out = [there]
                    while came[out[-1]] != start:
                        out.append(came[out[-1]])
                    return out[::-1]
                queue.append(there)
        return None

    # -- what the world makes, and what ends ----------------------------------------------------------------------

    def make_at(self, spec, area: str, line: Optional[int]) -> Optional[dict]:
        """An entity of spec at a free tile of the area, from the world's random; None if the area is full."""
        x0, y0, x1, y1 = self.definition.map.areas[area]
        tiles = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if self.free((x, y))]
        if not tiles:
            return None
        tile = tiles[self.rng.randrange(len(tiles))]
        entity = self.make(spec)
        entity['at'] = {'x': tile[0], 'y': tile[1]}
        entity['_home'] = [tile[0], tile[1]]
        self.put(self.entities, entity['id'], entity)
        self.dirty.add(entity['id'])
        self.reindex([entity['id']])
        self.mint_start(entity)
        return entity

    def spawn_now(self, name: str, area: str, count: int, for_ticks: Optional[int], line: Optional[int]) -> None:
        """q:spawn in a block: count more now, gone after for_ticks if given."""
        spec = self.definition.entities.get(name)
        if spec is None or spec.per_player:
            raise RuleError(f'q:spawn entity="{name}": not an entity of the world it may make', line)
        if area not in self.definition.map.areas:
            raise RuleError(f'q:spawn area="{area}": the map has no such area', line)
        for _ in range(count):
            entity = self.make_at(spec, area, line)
            if entity is None:
                break
            if for_ticks:
                entity['_expires'] = self.tick + for_ticks
                self.expiring.add(entity['id'])

    def remove(self, entity: dict) -> None:
        """An entity out of the world (its spawn makes another respawn= later); what it held, spent."""
        eid = entity['id']
        self.spend_all(entity, f'gone: {entity.get("kind")}')
        self.put(self.entities, eid, MISSING)
        self.gone.add(eid)
        self.dirty.discard(eid)
        self.travelers.discard(eid)
        self.expiring.discard(eid)
        index = entity.get('_spawn')
        if index is not None:
            kept = self.spawned[index]
            respawn = self.definition.spawns[int(index)].respawn_ticks
            self.put(kept, 'alive', [a for a in kept['alive'] if a != eid])
            self.put(kept, 'due', kept['due'] + [self.tick + respawn])
        self.reindex([eid])

    def kill(self, entity: dict, by: Optional[dict], line: Optional[int]) -> None:
        """q:kill: the on-death of its kind, then it goes (a player's stays: its on-death brings it back)."""
        eid = entity['id']
        if eid not in self.entities or eid in self.dying:
            return
        self.dying.add(eid)                    # an on-death that kills it again does nothing
        try:
            for death in self.definition.deaths:
                if entity.get('kind') in death.kinds:
                    self.rules.run(death.body, {death.as_name: entity, death.by_name: by})
        finally:
            self.dying.discard(eid)
        if entity.get('_player') is None and eid in self.entities:
            self.remove(entity)

    def loot(self, of: dict, to: dict, line: Optional[int]) -> None:
        """q:loot: the drops of an entity, rolled: an item to the receiver's bag, gold to its gold."""
        spec = self.definition.entities.get(of.get('_type'))
        if self.definition.ledger:                           # made by the ledger, booked as this kind's loot
            before, self.source = self.source, f'loot of {of.get("kind")}'
            try:
                for drop in (spec.loot if spec else []):
                    if self.rng.random() >= drop.chance:
                        continue
                    if drop.item is not None:
                        self.give(to, drop.item, self.rng.randint(*drop.count), None, None, line)
                    else:
                        self.give(to, None, None, self.rng.randint(*drop.gold), None, line)
            finally:
                self.source = before
            return
        for drop in (spec.loot if spec else []):
            if self.rng.random() >= drop.chance:
                continue
            if drop.item is not None:
                bag = to.get('bag')
                if not isinstance(bag, dict):
                    raise RuleError(f'q:loot: {to.get("id")} has no bag to put {drop.item} in (a field that is a '
                                    f'record: <q:field name="bag" value="{{ {{}} }}" />)', line)
                self.write(bag, drop.item, bag.get(drop.item, 0) + self.rng.randint(*drop.count), to, line)
            else:
                if not isinstance(to.get('gold'), (int, float)) or isinstance(to.get('gold'), bool):
                    raise RuleError(f'q:loot: {to.get("id")} has no gold to add to (a field that is a number)', line)
                self.write(to, 'gold', to['gold'] + self.rng.randint(*drop.gold), None, line)

    # -- a way, a step at a time ---------------------------------------------------------------------------------

    def travel(self, entity: dict, to: Tile, line: Optional[int]) -> None:
        here = self.tile_of(entity)
        if here is None:
            raise RuleError('q:travel: the entity is nowhere', line)
        path = self.way(here, lambda t: t == to, TRAVEL_SEARCH, entity['id'],
                        through=entity.get('_player') is not None)
        if path is None:
            raise Refused('No way there.')
        self.write(entity, '_path', [[x, y] for x, y in path], None, line)
        if path:
            self.travelers.add(entity['id'])

    def stop_travel(self, entity: dict, line: Optional[int]) -> None:
        if entity.get('_path'):
            self.write(entity, '_path', [], None, line)
        self.travelers.discard(entity['id'])

    # -- a tick of the world's own life ---------------------------------------------------------------------------

    def live(self) -> None:
        self.source = 'q:spawn'
        self._spawns()
        for eid in sorted(self.expiring):
            entity = self.entities.get(eid)
            if entity is not None and entity.get('_expires', 0) <= self.tick:
                self.remove(entity)
        for eid in sorted(self.travelers):
            self._go(eid)
        self._think()

    def _spawns(self) -> None:
        night = self.is_night()
        for i, sp in enumerate(self.definition.spawns):
            kept = self.spawned[str(i)]
            wanted = sp.night_count if night and sp.night_count is not None else sp.count
            missing = wanted - len(kept['alive']) - len(kept['due'])
            due = kept['due'] + [self.tick] * max(0, missing)
            later = [t for t in due if t > self.tick]
            alive = list(kept['alive'])
            spec = self.definition.entities[sp.entity]
            for _ in [t for t in due if t <= self.tick]:
                if len(alive) >= wanted:
                    continue                              # more than it keeps now (the night ended): not made
                entity = self.make_at(spec, sp.area, sp.line)
                if entity is None:
                    later.append(self.tick + 1)           # the area is full: the next tick
                    continue
                entity['_spawn'] = str(i)
                alive.append(entity['id'])
            kept['alive'], kept['due'] = alive, sorted(later)

    def _go(self, eid: str) -> None:
        entity = self.entities.get(eid)
        path = entity.get('_path') if entity else None
        if not path:
            self.travelers.discard(eid)
            return
        if entity.get('_until', 0) > self.tick:
            return
        self._begin()
        try:
            self.move(entity, (path[0][0], path[0][1]), None)
            self.write(entity, '_path', path[1:], None, None)
        except (RuleError, Refused):
            self._rollback()
            self.write(entity, '_path', [], None, None)   # blocked: the way ends here
            self.travelers.discard(eid)
            return
        self._commit()
        if not entity['_path']:
            self.travelers.discard(eid)

    def _think(self) -> None:
        cells = set()
        for hid in sorted(self.players.values()):
            tile = self.tile_of(self.entities.get(hid))
            if tile is not None:
                cells.update(self.cells_near(tile, AWAKE))
        awake = sorted({eid for cell in cells for eid in self.cells.get(cell, ())})
        self.source = 'q:brain'
        for eid in awake:
            entity = self.entities.get(eid)
            spec = self.definition.entities.get(entity.get('_type')) if entity else None
            if spec is None or not spec.states:
                continue
            self._begin()
            try:
                self._brain(entity, spec)
            except (RuleError, Refused) as e:
                self._rollback()
                self._error(f'q:brain of {eid}', e if isinstance(e, RuleError) else RuleError(f'refused: {e.reason}'))
                continue
            self._commit()

    def _become(self, entity: dict, state: str) -> None:
        self.write(entity, 'state', state, None, None)
        self.write(entity, '_since', self.tick, None, None)

    def _brain(self, entity: dict, spec) -> None:
        state = spec.states.get(entity.get('state')) or spec.states[spec.initial]
        local: Dict[str, Any] = {'it': entity}
        for condition, become, line in state.whens:
            if self.rules.expression(condition, local, line):
                if become != state.name:
                    self._become(entity, become)
                    state = spec.states[become]
                break
        if state.for_ticks is not None and self.tick - entity.get('_since', 0) >= state.for_ticks:
            self._become(entity, state.then)
            state = spec.states[state.then]
        if state.target is not None:
            found = self._entity(self.rules.expression(state.target, local, state.line))
            if (found['id'] if found else '') != entity.get('target', ''):
                self.write(entity, 'target', found['id'] if found else '', None, state.line)
        here = self.tile_of(entity)
        if here is None or entity.get('_until', 0) > self.tick or state.do == 'stand':
            return
        eid = entity['id']
        if state.do == 'wander':
            if self.rng.random() >= WANDER_CHANCE:
                return
            home = tuple(entity.get('_home') or here)
            ways = [(here[0] + dx, here[1] + dy) for dx, dy in STEPS]
            ways = [t for t in ways if self.free(t, eid) and _far(t, home) <= state.within]
            if ways:
                self.move(entity, ways[self.rng.randrange(len(ways))], state.line)
        elif state.do == 'chase':
            prey = self.entities.get(entity.get('target', ''))
            there = self.tile_of(prey) if prey else None
            if there is None or _far(here, there) <= 1:
                return
            path = self.way(here, lambda t: _far(t, there) <= 1 and t != there, CHASE_SEARCH, eid)
            if path:
                self.move(entity, path[0], state.line)
        elif state.do == 'flee':
            threat = self._entity(self.rules.expression(state.away_from, local, state.line))
            there = self.tile_of(threat) if threat else None
            if there is None:
                return
            ways = [(here[0] + dx, here[1] + dy) for dx, dy in STEPS]
            ways = [t for t in ways if self.free(t, eid) and _far(t, there) > _far(here, there)]
            if ways:
                self.move(entity, max(ways, key=lambda t: (_far(t, there), -STEPS.index((t[0] - here[0],
                                                                                         t[1] - here[1])))),
                          state.line)

    def _entity(self, x: Any) -> Optional[dict]:
        if isinstance(x, str):
            return self.entities.get(x)
        return x if self.is_entity(x) else None

    # -- what the expressions read of it --------------------------------------------------------------------------

    def nearest(self, x: Any, kind: Any, n: Any = AWAKE) -> Optional[dict]:
        """The nearest entity of that kind within n tiles of x (not x itself), the lowest id of the nearest."""
        tile = self.tile_of(x)
        me = x.get('id') if isinstance(x, dict) else x
        if tile is None:
            return None
        n = int(n)
        best = None
        for eid in sorted(self.near_ids(tile, n)):
            other = self.entities[eid]
            if eid == me or other.get('kind') != kind:
                continue
            far = _far(tile, self.tile_of(other))
            if far <= n and (best is None or far < best[0]):
                best = (far, other)
        return best[1] if best else None

    def fighting(self) -> List[dict]:
        """The entities next to the one they target (a fight: one blow each every so often)."""
        out = []
        for eid in sorted(self.entities):
            entity = self.entities[eid]
            prey = self.entities.get(entity.get('target') or '')
            if prey is None or (isinstance(entity.get('hp'), (int, float)) and entity['hp'] <= 0):
                continue
            a, b = self.tile_of(entity), self.tile_of(prey)
            if a is not None and b is not None and _far(a, b) <= 1:
                out.append(entity)
        return out

    def in_fight(self, x: Any) -> bool:
        entity = self._entity(x)
        if entity is None:
            return False
        return any(e is entity or e.get('target') == entity['id'] for e in self.fighting())

    def line_of_sight(self, a: Any, b: Any) -> bool:
        """No wall on the straight line between them."""
        ta, tb = self.tile_of(a), self.tile_of(b)
        if ta is None or tb is None:
            return False
        steps = _far(ta, tb)
        for k in range(1, steps):
            x = ta[0] + round((tb[0] - ta[0]) * k / steps)
            y = ta[1] + round((tb[1] - ta[1]) * k / steps)
            if (x, y) in self.definition.map.walls:
                return False
        return True

