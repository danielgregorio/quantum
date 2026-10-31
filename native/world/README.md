# native/world: the world's engine

The game server's engine in Rust ([PLAN_WORLD_ENGINE.md](../../PLAN_WORLD_ENGINE.md)). A world is still written in
Quantum's tags (`q:application type="gameserver"`), and Python still reads it. This crate is what runs it, on every
core, built by maturin into the Python module `quantum_world`.

E1 is built. The tick is still Python's `World.step`. After each tick the engine:

- **Works out what each player is told** (`src/frames.rs`, a player per task on rayon's pool): who comes into
  each view, the fields that changed, who leaves, and the events. It keeps its own copy of what players can see
  and its own index of 16-tile cells. Its frames are those of `quantum/runtime/gameserver/frames.py`, to the byte;
  `tests/gameserver/test_gameserver_native.py` and `quantum gameserver conform --against rust` hold it to them.
- **Holds the network** (`src/net.rs`, on tokio). It reads every message and checks its size, its rate, and a
  command's seq and name. It answers the pings and writes each player's frames, so the tick's thread never waits
  on a socket. A hello and its ticket, and a test world's step, sync and peek, are the world's to decide: they
  go to Python (`quantum/runtime/gameserver/native.py`) in the order they came.

E2 is built: **the rules as bytecode** (`src/vm.rs`). Python compiles each expression and each block of a world
(`quantum/runtime/gameserver/bytecode.py`: a q:command's, a q:function's, a rule's) into instructions for a stack
machine, and the machine runs them with the Core's meaning, to the value and to the error's last word: numeric
texts, Python's `/`, `//` and `%`, `round` half away from zero, the stdlib, Python's TypeErrors and the Core's "did
you mean" (difflib's, `src/vm.rs`). Loops, q:set, q:if, q:require, q:call and q:return run in the machine; a
world's functions and what only the world does (a q:move, a q:emit, the ledger's) it asks of the world
(`quantum/runtime/gameserver/machine.py`). Python's random, word for word, is `src/rng.rs`, for E3.

E3 is under way: **the world's state** (`src/world.rs`). E3a holds a world's core (its entities, variables and
players, joins and leaves, commands, q:every, q:on-join, q:on-leave, q:move, q:emit, q:say, its index, snapshot and
digest) to the byte of `quantum/runtime/gameserver/world.py`'s; `quantum/runtime/gameserver/native_world.py`
hands it the definition and keeps Python's view of it in step. A world that needs more stays Python's, told why.

The world's values are compared as Python compares them and written as Python's `json.dumps` writes them
(`src/value.rs`).

```bash
pip install ./native/world                        # build the module (Rust and maturin)
quantum gameserver run world.server.q --engine rust
quantum gameserver run world.server.q --rules machine          # its rules as bytecode, on the machine
quantum gameserver bytecode world.server.q --blocks            # each block as the machine runs it
QUANTUM_WORLD_ENGINE=rust QUANTUM_WORLD_RULES=machine pytest tests/gameserver   # the game server's tests, on it
python scripts/bytecode-fuzz.py --draws 1000000                # a million expressions, both ways

cd native/world
cargo test --no-default-features                  # the engine's own tests, without a Python
cargo clippy --all-targets -- -D warnings
```

Without the module, Quantum runs the Python engine and says so. A machine where you only try a world needs no Rust.
CI builds and tests it in `.github/workflows/world-engine.yml`.
