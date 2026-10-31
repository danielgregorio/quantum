"""A world whose state and tick are the Rust engine's (PLAN_WORLD_ENGINE.md, E3): native/world/src/world.rs runs it,
to the byte of world.py's digest, and the machine (vm.rs) runs its blocks with the world as its host.

Python still reads the .q (model.py) and compiles it (bytecode.py); `export` hands the engine the definition with
every block, field and variable as bytecode. E3a holds the world's core: its entities, variables and players, joins
and leaves, the commands, q:every, q:on-join and q:on-leave, q:move, q:emit and q:say, and the functions that read the
world. A world that needs more (spawns, brains, the ledger, parties, trades, quests, NPCs: E3b and E3c) is found
here first, by name, and stays world.py's.

`NativeWorld` is a World whose step is the engine's: after each tick it takes what changed (the entities written or
gone, the players, the variables, the events, the errors) into its own dicts, so frames.py, the views and the server
read it as they read world.py's.

    world = NativeWorld(definition)          # NotNative(reasons) when it needs what the engine has not yet
    out = world.step([('join', 'ana')])
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from quantum.runtime.gameserver.bytecode import (CompileError, OP, compile_block, compile_value,
                                                 world_function_names)
from quantum.runtime.gameserver.world import Event, TickOut, World

try:
    import quantum_world
except ImportError:  # not built here
    quantum_world = None

# what the engine's host runs itself (world.rs's WORLD_FUNCTIONS) and the statements it does (its effect)
NATIVE_FUNCTIONS = frozenset({'tile', 'walkable', 'ahead', 'distance', 'near', 'in_area', 'area', 'heroes',
                              'entities', 'entity', 'tick', 'seconds', 'random', 'chance', 'pick', 'now', 'sqrt',
                              'nearest', 'fighting', 'in_fight', 'sees', 'is_night', 'daytime'})
NATIVE_EFFECTS = frozenset({'move', 'emit', 'say'})


class NotNative(Exception):
    """A world that needs what the engine does not hold yet: the reasons, by name."""

    def __init__(self, reasons: List[str]):
        self.reasons = reasons
        super().__init__('; '.join(reasons))


def _uses(code) -> Tuple[set, set]:
    """The world's functions a code calls, and the statements it hands the world."""
    calls, effects = set(), set()
    for op, a, _ in code.ops:
        if op in (OP['CALL_HOST'], OP['CALL_HOST_KW']):
            calls.add(code.names[a])
        elif op == OP['EFFECT']:
            effects.add(code.consts[a])
    return calls, effects


def export(definition, interpreter) -> Tuple[Dict[str, Any], List[tuple]]:
    """The definition as the engine reads it (world.rs's WorldDef), with its codes: (definition, codes). NotNative
    when the world needs more than the engine holds."""
    d = definition
    reasons: List[str] = []
    for what, present in (('q:spawn', d.spawns), ('q:on-death', d.deaths), ('the ledger', d.ledger),
                          ('q:quest', d.quests), ('q:npc', d.npcs), ('q:chat', d.chat), ('q:party', d.party_size),
                          ('q:trade', d.trade)):
        if present:
            reasons.append(f'{what} (E3b, E3c)')
    for name, e in d.entities.items():
        if e.states or e.loot:
            reasons.append(f'the brain or the loot of {name} (E3b)')
    for name, c in d.commands.items():
        if c.builtin:
            reasons.append(f'the command {name}, the world\'s own (E3c)')
    own = world_function_names(interpreter)
    users = frozenset(d.functions)
    codes: List[tuple] = []
    calls, effects = set(), set()

    def add(code) -> int:
        c, e = _uses(code)
        calls.update(c)
        effects.update(e)
        codes.append((code.ops, code.consts, code.names))
        return len(codes) - 1

    def block(element, where: str) -> int:
        try:
            return add(compile_block(element, d, own, users, where))
        except CompileError as e:
            reasons.append(f'{where}: {e}')
            return -1

    def value(raw: str, line: Optional[int], where: str) -> int:
        try:
            return add(compile_value(raw, d, own, users, line or 0, where))
        except CompileError as e:
            reasons.append(f'{where}: {e}')
            return -1

    m = d.map
    out = {
        'name': d.name, 'tick_rate': d.tick_rate, 'players': d.players,
        'map': {'width': m.width, 'height': m.height, 'walls': sorted([x, y] for x, y in m.walls),
                'areas': {name: list(box) for name, box in m.areas.items()}},
        'entities': {name: {'kind': e.kind, 'per_player': e.per_player, 'persist': e.persist,
                            'step_ticks': e.step_ticks,
                            'fields': [{'name': f.name, 'value': value(f.value, f.line, f'{name}.{f.name}'),
                                        'private': f.private} for f in e.fields]}
                     for name, e in d.entities.items()},
        'hero': d.hero.name,
        'commands': {name: {'params': list(c.params), 'limit': list(c.limit) if c.limit else None,
                            'body': block(c.body, f'q:command {name}') if c.body is not None else -1, 'by': c.by}
                     for name, c in d.commands.items()},
        'functions': {name: {'params': list(f.params), 'body': block(f.body, f'q:function {name}'),
                             'line': f.line or 0} for name, f in d.functions.items()},
        'every': [[ticks, block(rule, 'q:every')] for ticks, rule in d.every],
        'on_join': [block(b, 'q:on-join') for b in d.on_join],
        'on_leave': [block(b, 'q:on-leave') for b in d.on_leave],
        'variables': [[name, value(raw, line, name)] for name, raw, line in d.variables],
        'spawns': len(d.spawns), 'day_ticks': d.day_ticks, 'night': d.night,
    }
    reasons += [f'the function {name}() (E3b, E3c)' for name in sorted(calls - NATIVE_FUNCTIONS)]
    reasons += [f'<q:{name}> (E3b, E3c)' for name in sorted(effects - NATIVE_EFFECTS)]
    if reasons:
        raise NotNative(reasons)
    return out, codes


def native_ok(definition) -> Optional[List[str]]:
    """None when the engine runs this world's state; else what it does not hold yet."""
    if quantum_world is None:
        return ['the Rust engine is not built here (pip install ./native/world)']
    try:
        export(definition, World(definition).rules)
    except NotNative as e:
        return e.reasons
    return None


class NativeWorld(World):
    """A World whose state and tick are the engine's; its own dicts are kept in step after each tick, for what reads
    it (frames.py, the views, the server)."""

    def __init__(self, definition, seed: int = 0, _native=None):
        if quantum_world is None:
            raise NotNative(['the Rust engine is not built here (pip install ./native/world)'])
        super().__init__(definition, seed)
        self._exported, self._codes = export(definition, self.rules)
        self.native = _native or quantum_world.World(self._exported, self._codes, seed)
        self._errors_made = 0
        self._take(sorted(self.native.snapshot()['entities']))

    def _take(self, ids=None) -> None:
        """What the engine's tick changed (or these entities), into these dicts."""
        dirty, gone, players, vars_, vars_changed, events, errors, made = self.native.changes(self._errors_made)
        if ids is None:
            ids = sorted(set(dirty) | set(gone))
        for eid, entity in self.native.pull(list(ids)).items():
            if entity is None:
                self.entities.pop(eid, None)
            else:
                self.entities[eid] = entity
        self.dirty, self.gone = set(dirty), set(gone)
        self.players, self.vars, self.vars_changed = players, vars_, vars_changed
        self.events = [Event(message, tuple(tile) if tile else None, to, everyone, accounts)
                       for message, tile, to, everyone, accounts in events]
        self.errors.extend(errors)
        del self.errors[:-100]
        self._errors_made = made
        self.tick = self.native.tick
        self.reindex(self.dirty | self.gone)

    def step(self, inputs: List[tuple]) -> TickOut:
        raw = self.native.step(inputs)
        out = TickOut(raw['tick'], entries=raw['entries'], acks=raw['acks'], refused=raw['refused'],
                      joined=raw['joined'], left=raw['left'], full=raw['full'])
        self._take()
        return out

    def snapshot(self) -> dict:
        return self.native.snapshot()

    def digest(self) -> str:
        return self.native.digest()

    @classmethod
    def from_snapshot(cls, definition, snap: dict) -> 'NativeWorld':
        world = cls(definition)
        world.native = quantum_world.World.from_snapshot(world._exported, world._codes, snap)
        world.entities, world.stored = {}, {}
        world.cells, world.cell_of = {}, {}
        world._take(list(snap['entities']))
        return world
