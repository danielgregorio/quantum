"""The game compiler: a `q:application type="game"` to a Godot 4 project.

Thin compiler, fat runtime (PLAN_GAMES_2.md):

- `schema.py` says which tags and attributes exist. An unknown one is a
  compile error with its line, never a comment in the output.
- `model.py` reads the XML elements into a game model and checks them
  against the schema; `q:set`, `q:if`, `q:loop`, `q:function` are read here
  too, so a `qg:` action may sit inside a `q:if`.
- `expressions.py` compiles a Quantum expression (`{coins + 1}`) to GDScript.
- `statements.py` compiles the statements and action tags to GDScript.
- `compiler.py` writes the project: `game.json` (everything declarative),
  `scripts/*.gd` (the compiled logic), `addons/quantum/` (the runtime,
  copied as it is), `project.godot` and the assets.

The runtime, `addons/quantum/*.gd`, builds the scene tree from `game.json`
and runs the game; nothing in it is generated.
"""

from quantum.runtime.godot.compiler import compile_game  # noqa: F401
from quantum.runtime.godot.errors import GameCompileError  # noqa: F401
