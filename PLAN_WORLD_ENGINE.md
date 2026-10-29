# The world's engine — Quantum's tags above, Rust beneath

> Status: approved 2026-10-29. The owner's ask: the world is still written in Quantum's tags
> (`q:gameserver`, `PLAN_GAME_SERVER.md`), but what runs it is Rust, and on every core of the machine.
> It comes after PR #95 (Phases 2 to 5) and before Phase 6 of `PLAN_GAME_SERVER.md`; it takes the place of
> "PyPy if the numbers ask for it" in that plan's Phase 7.

## Why

The plan's promise is five hundred players and fifteen hundred beasts, a tick (ten a second) within 50 ms at the
99th percentile. Today's server is Python, one thread, and the numbers say it does not hold
(`scripts/gameserver-bots.py`, a 96 by 96 field, the bots on the same four-core machine as the server):

| Bots | Tick, median | Tick, 99th percentile | Worst | Each player receives |
|---|---|---|---|---|
| 100 (an hour) | 9.4 ms | 17.6 ms | 216 ms | 1.16 KB/s |
| 200 | 27.6 ms | 48.9 ms | 65 ms | 1.73 KB/s |
| 500 | 91 ms | 177 ms | 242 ms | 3.14 KB/s |

At five hundred the tick is past its own 100 ms: the world falls behind. Where the time goes, measured with cProfile
at 200 bots (606 ticks):

| Part of the tick | Share | What it is |
|---|---|---|
| Who sees what, and sending it | 71% | each player's views read again (`World.members`, `sees`, `tile_of`: three million calls), what changed in them, JSON, the WebSocket writes |
| The rules of the tags | 26% | the commands the players sent, run by the interpreter (`rules.py`: `q:set`, `q:require`, the expressions) |
| The beasts | 3% | spawns, brains, the ways they walk |

Three quarters of the tick is mechanical: an index, sets, differences, bytes to sockets. That is what a compiled
language does many times faster, and what spreads over cores. The quarter that is the tags' is small, but it is
interpreted on Python's tree of each expression.

## The decision

The same split as the games and the Hive's screen. A game is written in `qg:` tags and runs on Godot (C++); the
Hive's screen is a `q:application type="screen"` drawn by Rust (`os/crates/hive-screen`). A world will be:

- **The tags are the language.** Nothing an author writes changes: the same `.q`, the same expressions, the same
  checks when it is compiled, the same reference (`docs/targets/gameserver.md`).
- **Python is the compiler.** It reads the `.q`, checks it against the schema (every error it names today, with its
  line), and writes the world compiled: its definition, and each rule, expression and view as bytecode.
- **Rust is the engine.** It holds the world's state, runs the tick, the bytecode, the beasts, the index and the
  views, writes the log, and speaks the protocol to every player. One process, every core.

Rust, not C++: the server is open to the internet, and Rust gives memory safety at C++'s speed. PyO3 and maturin
join it to Python cleanly, and the repository builds Rust in CI already (`os/`, `.github/workflows/os.yml`).

## One semantics, guarded by the log

A world is deterministic: a snapshot and the inputs after it are the world. That is also how the two engines are
held to one meaning. **The same snapshot and the same log, run by the Python engine and by the Rust engine, give the
same world on every tick**: the same `digest()`, the same acks and refusals, the same frames to each player. The
Python engine stays as the reference (and for a machine with no build of the engine). The conformance harness runs
both on every test world (meadow, den, Outpost) and on hours of recorded bot sessions, in CI.

What has to match exactly, and is easy to get wrong:

- **The random.** Python's `random.Random` (Mersenne Twister, and how `random()`, `randint`, `randrange` and the
  picks draw from it), reproduced bit for bit, so an old log replays the same.
- **The numbers.** A whole number has no limit in Python (the engine uses 64 bits and refuses an overflow by name);
  `/` is a float, `//` floors, `%` takes the divisor's sign, `round` goes to even, a float prints as Python's `repr`.
- **The texts and the order.** Records keep the order their keys came in (`indexmap`); a list sorts as Python's
  does; a text is Unicode code points, as `len()` counts them.
- **The JSON.** The frames' fields and values are the same (the key order may differ: the clients read objects).

## How it runs on every core

The world's writes stay on **one thread**, in the order the inputs arrived. That is what makes the world
deterministic: two commands on two threads would run in an order the threads' timing chose, and the log would no
longer be the world. Every MMO server keeps a zone's simulation on one thread for this reason. Everything around it
runs in parallel, so that thread does nothing but the rules:

| Work | Threads | How |
|---|---|---|
| The network | a pool (tokio, one per core) | accept, the hello and its ticket, read and parse each command, check its size and rate, write each player's frames; a slow player never holds the tick |
| Who sees what | a pool (rayon) | after the tick the world is read only: each player's views, their differences and their JSON are made in parallel, a player per task |
| The beasts' brains | the same pool | each beast decides from the world as it is (its target, its way, a breadth-first search round walls) in parallel; the decisions are then applied in the order of the beasts' ids, on the tick's thread |
| The log | its own thread | the tick's lines written and synced before its acks go out, as today; a snapshot made from a copy of the state, off the tick |
| The minds of the NPCs | Python, off the tick | as today (`npc.py`): the engine hands a `q:ask` over and gets the answer back as an input of a later tick |
| Later: rooms | a thread each | a `q:room` (Phase 7) is a world of its own, with its own tick thread |

And the tick is a pipeline: while tick N's frames go out on the network threads, tick N+1's inputs are being
gathered, so the tick's thread never waits on a socket or a disk.

## What moves where

| Today (Python) | In the engine (Rust) |
|---|---|
| `world.py`: entities as dicts, the journal, the index of cells | an entity store (ids to slots, fields as values), a journal of what each write replaced, a grid of 16-tile cells |
| `rules.py`, `expressions.py`: the interpreter on Python's tree of each expression | a bytecode virtual machine; the compiler (Python) writes the bytecode, the engine runs it |
| the world's functions (`near`, `nearest`, `balance`, `party_of`...) | the same functions, native |
| `life.py`, `ledger.py`, `together.py`: spawns, brains, travel, the books, chat, party, trade, quests | the same, native, with the brains thinking in parallel |
| `server.py`: views, differences, JSON, WebSockets, tickets | tokio and tungstenite for the network, serde for JSON (MessagePack later), HMAC for the tickets |
| `log.py`: snapshot and lines | the same files and the same format: an old world's data goes on in the new engine |
| `npc.py`: the minds | stays Python: the engine calls it off the tick |
| `session.py`, `WorldTable`, the play protocol | unchanged: they speak the protocol, whatever runs the world |

What does not change: the `.q` language, the protocol, the game's side (Godot), the log's format, the CLI
(`quantum gameserver run`, `check`, `ticket`; `--engine rust|python` chooses, Rust once it is there).

## The phases

### E0 — The gauge (S)

The two measures the rest is held to. The load: `gameserver-bots.py` gains a mode with the bots on other cores, or
another machine, and a map like Outpost's, and writes a table of numbers per run; 500 bots and 1500 beasts. The
sameness: `quantum gameserver conform WORLD LOG` runs a world's log on two engines and names the first tick where
they part (the digest, an ack, a refusal, a frame). With one engine it checks the replay against the recorded run.

Done when: the numbers above are reproduced by one command, and the harness passes for the Python engine against
itself on every test world.

### E1 — The engine sends (L)

The 71% first, without touching the rules. A crate `native/world` (PyO3, built by maturin into the module
`quantum_world`) takes the network and the views: the tick's thread is still Python's `World.step`, and after it the
engine gets what changed (the dirty entities' public and private fields, their tiles, what left, the events). It keeps
its own copy of what players can see, works out each player's views and frames on the pool, and writes them to the
sockets. A view whose `where=` is more than `near(it, me, n)` runs its condition on the bytecode of E2; until then,
on the Python evaluator, called for those views only.

Done when: `tests/gameserver` and the Godot world tests pass with `--engine rust`; at 500 bots the views and the
sending take under a fifth of what they take today, measured by E0.

### E2 — The rules compile (L)

The language as bytecode. The Python compiler turns each expression and each block of statements of a world
(`q:set`, `q:if`, `q:loop`, `q:call`, `q:return`, `q:require`, `q:move`, `q:emit`, `q:spawn`, `q:kill`, `q:loot`,
`q:travel`, `q:give`, `q:take`, `q:pay`, `q:say`, `q:ask`, `q:reward`) into bytecode, and the engine's virtual
machine runs it, with the Core's operators and stdlib and the world's functions. Python's random and numbers, as
above. Tested on its own first: every expression of the test worlds, and generated expressions from the grammar, give
the same value both ways.

Done when: every expression and block of every test world and of Outpost runs the same in the VM as in the
interpreter, and the generated expressions agree on a million draws.

### E3 — The world in Rust (L)

The state moves: the entity store, the journal and the undoing of a refused command, joins and leaves, the rules due
(`q:every`, `q:on-join`, `q:on-death`), spawns, brains (thinking in parallel, as above), travel, the ledger and its
books, chat, parties, trades, quests, and the hand-off of a `q:ask`. Snapshots and the log, the same files. The
tick's thread no longer takes Python's lock at all.

Done when: the conformance harness passes, Python against Rust, on every test world and on a day of recorded bots;
Outpost plays from start to end on the Rust engine (`tests/gameserver/test_outpost.py`); an old world's data
continues on it.

### E4 — Five hundred (M)

The numbers of `PLAN_GAME_SERVER.md` for a day of bots: 500 players, 1500 beasts, the tick within 50 ms at the 99th
percentile, a restart that loses no command acknowledged, memory under 1.5 GB. MessagePack as a choice of the
protocol if what players receive asks for it. Then Phase 7 goes on with the container on the homelab, behind the
tunnel.

Done when: the table of E0 holds for a day, on the machine the world will live on.

## Building and shipping it

- The crate lives in `native/world/` (its own Cargo workspace, not `os/`'s). maturin builds wheels: Linux x86-64 and
  ARM (the homelab), macOS for working on it. CI builds and tests them (a job beside `os.yml`'s), and runs the
  conformance harness.
- Without a wheel, Quantum runs the Python engine and says so: a machine to try a world on needs no Rust.
- The crates it uses: pyo3, tokio, tokio-tungstenite, serde and serde_json, rayon, indexmap, hmac and sha2,
  crossbeam-channel; rmp-serde in E4.

## Risks

- **Two engines to keep the same.** Every rule the language gains is written twice, and the harness is what catches
  a difference. The Python engine could be retired once the Rust one has run a season; that is a later decision.
- **Python's exact behaviour.** The random, the numbers, the order of records: the harness finds a difference on the
  tick it happens; the cost is finding all of them before E3 is done.
- **The bridge of E1.** Handing each tick's changes from Python to Rust costs time; it is measured in E1, and E3
  removes it.
- **The size.** About 4,500 lines of Python become an engine; the phases are cut so that each one ships and is
  measured on its own.

## What it is not

Not a new language: an author never writes Rust. Not a change to the protocol or to the game's side. Not
parallel rules: a zone's world is one thread of writes, on purpose, so that its log is the world.
