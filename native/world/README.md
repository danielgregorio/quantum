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

The world's values are compared as Python compares them and written as Python's `json.dumps` writes them
(`src/value.rs`).

```bash
pip install ./native/world                        # build the module (Rust and maturin)
quantum gameserver run world.server.q --engine rust
QUANTUM_WORLD_ENGINE=rust pytest tests/gameserver  # the game server's tests, on the engine

cd native/world
cargo test --no-default-features                  # the engine's own tests, without a Python
cargo clippy --all-targets -- -D warnings
```

Without the module, Quantum runs the Python engine and says so. A machine where you only try a world needs no Rust.
CI builds and tests it in `.github/workflows/world-engine.yml`.
