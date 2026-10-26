"""A game's server, as a Quantum application: `q:application type="gameserver"` (PLAN_GAME_SERVER.md).

- `schema.py` says which tags a world has; one with no entry does not exist, and says so with its line.
- `model.py` reads the file against it into a `WorldDef`: the map, the entities, the commands, the rules.
- `expressions.py` and `rules.py` run its statements and expressions: the Core's, with the world's functions and
  its seeded random, every write journaled so a refused command is undone whole.
- `world.py` is the world a tick at a time: `World.step(inputs)`, the same inputs giving the same world.
- `log.py` keeps it: a snapshot now and then and every input after it; a restart replays them.
- `server.py` is `quantum gameserver run`: the world on a WebSocket, its protocol and its clock (or a test's).
- `session.py` is the play protocol's door: `WorldSession`, `serve_world`.
"""

from quantum.runtime.gameserver.errors import GameServerError, Refused, RuleError  # noqa: F401
from quantum.runtime.gameserver.model import WorldDef, read_world  # noqa: F401
from quantum.runtime.gameserver.world import World  # noqa: F401
