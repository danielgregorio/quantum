# The world's engine — Quantum's tags above, Rust beneath

> Status: approved 2026-10-29. The owner's ask: the world is still written in Quantum's tags
> (`q:gameserver`, `PLAN_GAME_SERVER.md`), but what runs it is Rust, and on every core of the machine.
> It comes after PR #95 (Phases 2 to 5) and before Phase 6 of `PLAN_GAME_SERVER.md`; it takes the place of
> "PyPy if the numbers ask for it" in that plan's Phase 7.
> E0 done (2026-10-29): `quantum gameserver conform` and the load's gauge; the Python engine's numbers, with players
> alone and with 1500 beasts, are in the record below. With the beasts, their brains are 85% of the tick.
> E1 done (2026-10-30): `native/world`, the views and the network in Rust (`--engine rust`), to the byte the Python
> engine's frames; at 500 bots the views and the sending went from 61 ms of the tick to 10.5, and the tick from 79 ms
> to 29 (48 at the 99th percentile). With 1500 beasts the rules are the tick now: E2 and E3.

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

## Record

### E0 (2026-10-29)

Built: `frames.py`, what each player is told of a tick, made apart from the network (the server sends it; the
harness compares it); `quantum gameserver conform`, against the record or a second engine; `quantum gameserver run
--digest-every`; and in `scripts/gameserver-bots.py`, `--beasts`, `--world` (a world of a site's accounts gets a
ticket for each bot), `--url`, the server and the bots on half the cores each, and `--sweep`. The harness passes for
the Python engine against itself on meadow, den and Outpost, and finds a forged result, a forged digest, a field
written on one tick and a frame said once more on the tick they happen
(`tests/gameserver/test_gameserver_conform.py`).

The Python engine, four cores (two for the server, two for the bots), a 96 by 96 field, a view of 9 tiles:

    python scripts/gameserver-bots.py --sweep 100,200,500 --seconds 60

| Bots | Beasts | Tick, median | Tick, 99th percentile | Worst | Each player receives | Memory | Dropped |
|---|---|---|---|---|---|---|---|
| 100 | 0 | 11.1 ms | 21.8 ms | 29.9 ms | 1.17 KB/s | 47 MB | 0 |
| 200 | 0 | 23.7 ms | 89.1 ms | 382.2 ms | 1.73 KB/s | 54 MB | 0 |
| 500 | 0 | 76.9 ms | 125.9 ms | 137.5 ms | 3.57 KB/s | 74 MB | 0 |

    python scripts/gameserver-bots.py --bots 500 --beasts 1500 --seconds 240

| Bots | Beasts | Tick, median | Tick, 99th percentile | Worst | Each player receives | Memory | Dropped |
|---|---|---|---|---|---|---|---|
| 500 | 1500 | 372.5 ms | 630.2 ms | 658.0 ms | 2.86 KB/s | 81 MB | 0 |

With the plan's load the world runs fewer than three ticks a second, of its ten: the bots sent 362,485 steps in four
minutes and 84,306 ran. Where the tick goes with 100 bots and 1500 beasts (cProfile, 93 ticks): the beasts' brains
85% (their `q:when` conditions, evaluated by the interpreter for each beast every tick, half of it, and `nearest`
reading the index, a third), the views and the sending 10%. With players alone it was the other way round: the views
and the sending 71%, the rules 26%, the beasts 3%.

So the order stays, and what each phase buys is clearer: E1 takes the players' share; the beasts' share is E2's
bytecode and E3's brains thinking in parallel. A cost found on the way, fixed in Python because it was the
algorithm's and not the language's: a spawn of many beasts listed an area's free tiles tile by tile, for each beast
(200 beasts took 6.6 s on the first tick); they are read from the index's cells now, the same tiles in the same
order, so the same draw lands on the same tile.

### E1 (2026-10-30)

Built: `native/world`, a crate of its own that maturin builds into the module `quantum_world`
(`pip install ./native/world`; PyO3, abi3, Python 3.12 and later). `quantum gameserver run --engine rust` (or
`QUANTUM_WORLD_ENGINE=rust`) runs a world on it; the default stays `python` until E3, and where the module is not
built the Python engine runs the world and says so.

- **What each player is told** (`src/frames.rs`). The tick is still `World.step`. After it the engine is handed the
  dirty entities as they are now, those gone, the acks, the refusals and the events. It keeps its own copy of what
  players see (each entity as the others see it and as its own player does, and its JSON, written once a change)
  and its own index of cells, and works out every player's frames on rayon's pool, a player per task. Values are
  compared as Python compares them (1 == 1.0 == True) and written as `json.dumps` writes them (ensure_ascii, a
  float as its repr), so the frames are frames.py's to the byte: `tests/gameserver/test_gameserver_native.py`
  compares the texts, every player, every tick, on meadow, den and Outpost, and `quantum gameserver conform
  --against rust` compares the frames, the acks and the digests. A view whose `where=` is more than the near()
  (meadow's `loud`) has its members read by the interpreter, for those views only (frames.py's `view_members`,
  which both engines use); the engine works out what changed in them.
- **The network** (`src/net.rs`, tokio and tungstenite). Every message is read and checked on the engine's threads
  (16 KB, sixty a second, a command's integer seq and its name); the pings are answered, and sent every twenty
  seconds as websockets does; each player's frames are written from a queue of its own, so a slow player no longer
  holds the tick (one sixteen megabytes behind is let go). A hello and its ticket, and a test world's step, sync
  and peek, are the world's to decide: they go to Python (`native.py`) in the order they came, and a connection's
  next message is read only once its hello is answered, as server.py's handler did.

The whole of `tests/gameserver` and the Godot world tests (world, den, Outpost, sign-in) pass on it, 153 tests; CI
runs them on it in `.github/workflows/world-engine.yml`, with `cargo fmt`, `clippy` and the engine's own tests.

The gauge, the same machine as E0's (four cores: two for the server, two for the bots), a 96 by 96 field, a view of
9 tiles; the server's numbers now say the rules' share of the tick (`World.step`) and the sending's (the frames, the
JSON, the sockets):

    python scripts/gameserver-bots.py --sweep 100,200,500 --seconds 60 --engine rust

| Engine | Bots | Beasts | Tick, median | Tick, 99th percentile | Worst | The rules, median | Views and sending, median | Each player receives | Memory | Dropped |
|---|---|---|---|---|---|---|---|---|---|---|
| python | 500 | 0 | 78.69 ms | 150.1 ms | 170.76 ms | 13.56 ms | 60.62 ms | 3.43 KB/s | 76 MB | 0 |
| rust | 100 | 0 | 7.04 ms | 11.62 ms | 19.61 ms | 3.96 ms | 1.68 ms | 1.22 KB/s | 56 MB | 0 |
| rust | 200 | 0 | 11.42 ms | 35.35 ms | 82.89 ms | 7.07 ms | 3.17 ms | 1.8 KB/s | 71 MB | 0 |
| rust | 500 | 0 | 28.97 ms | 47.93 ms | 54.71 ms | 16.65 ms | 10.5 ms | 3.37 KB/s | 117 MB | 0 |
| rust | 500 | 1500 | 262.78 ms | 444.91 ms | 452.44 ms | 227.06 ms | 28.2 ms | 4.29 KB/s | 139 MB | 0 |

At 500 bots the views and the sending take 10.5 ms of the tick where they took 60.6: under a fifth, as E1 asked.
The tick is 29 ms where it was 79, within the plan's 50 ms at the 99th percentile for players alone. Of the
engine's share, at 500 players in process, reading what changed out of Python (the bridge, which E3 removes) is
1.0 ms and the frames 2.2 ms; the rest is the sockets' and the threads'. The rules took a little longer on the Rust
engine's runs (16.7 ms against 13.6): the same two cores now also run the engine's threads.

With 1500 beasts the tick is 263 ms where it was 372 (E0), and the rules are 227 ms of it: the beasts' brains, as
E0 found. So the order stays: E2's bytecode for their `q:when`s, and E3's brains thinking in parallel. Memory is
higher on the engine (117 MB against 76 at 500 bots): its copy of what players see and each connection's queue.


### E2 (2026-10-30)

Built: the rules as bytecode. `quantum gameserver run --rules machine` (or `QUANTUM_WORLD_RULES=machine`) runs a
world's blocks and expressions on the engine's machine; the default stays the interpreter until E3, and where the
module is not built the interpreter runs them and says so. It is orthogonal to `--engine`: CI runs the game
server's tests on the Rust engine with the rules on each.

- **The compiler** (`quantum/runtime/gameserver/bytecode.py`). Python reads an expression as the Core reads it (the
  same parse, the same checks) and writes it for a stack machine: 37 instructions, each an opcode and two numbers.
  A block (a q:command's, a q:function's, a q:every's, an on-join's, an on-death's) is compiled whole, statement by
  statement, each with its line: q:set of a name, of a world's variable and of a path; q:if with its elseifs;
  q:loop over items or a range; q:call; q:return; q:require; and the world's statements (q:move, q:emit, q:give,
  q:kill and the rest), whose attributes the machine evaluates in the interpreter's order before it hands them to
  the world. What the machine does not hold (a set, the stdlib's dates and passwords, a q:spawn whose count does
  not read) is refused by name, and that block, and what calls it, stays the interpreter's. `quantum gameserver
  bytecode world.server.q` shows each expression as the machine runs it, `--blocks` each block.
- **The machine** (`native/world/src/vm.rs`). The Core's meaning, to the value and to the error's last word: numeric
  texts in arithmetic and comparison, `/` a float, `//` and `%` floored as Python's, `round` half away from zero
  over the number's text, `and`/`or` giving an operand, chained comparisons, the stdlib's arguments bound as Python
  binds them (its TypeErrors word for word), the Core's "did you mean" (difflib's matcher, in Rust), the TypeError
  Python raises past the Core (`-[1]`), the comparison a failed sort names (CPython's run and binary insertion, as
  3.12 and 3.13 each do them). Python's numbers past 64 bits and complex results are refused by name. The
  q:functions run on the machine, with the interpreter's depth (64) and its wording of a call that fails inside
  an expression (`f() failed: line 9: ...`). Python's random is `src/rng.rs`, word for word, for E3.
- **The world as its host** (`quantum/runtime/gameserver/machine.py`, `src/python.rs`). The state is still Python's:
  an entity reaches the machine as its id and its fields are read from its dict; a run holds each entity it met as
  the dict it was, so one a q:loop killed is still what it was to the rest of the loop, as it is to Python. The
  world's variables, its functions (`near`, `nearest`, `random`...) and what only it does are asked of it. A block
  run from inside an effect (a q:kill's on-death) runs on the same machine.

Held to the interpreter three ways. Every expression and every block of the test worlds and of Outpost compiles (174
expressions, 54 blocks; every q:function on the machine). A million expressions drawn from the grammar agree
to the value and to the error's text and type, on Python 3.12 and on 3.13 (`python scripts/bytecode-fuzz.py`: 0
differences on each, in about five minutes; four results past 64 bits and 726 complex numbers counted apart, not
compared). And the worlds run tick by tick:
`tests/gameserver/test_gameserver_blocks.py` plays sessions of meadow, den and Outpost on both and compares the
digest every tick, the frames and the errors the worlds keep, word for word, and sends a world of cases (40
commands) what is hardest for each statement. The whole of `tests/gameserver` (202 tests) passes with the rules on
the machine, on 3.12 and 3.13; CI runs it, with the Godot world tests, so.

That found one thing the expressions alone had not: an entity a loop held by id was gone once struck dead (den's
blow a second), so the rat never died. A run now holds each entity as its dict.

What stays apart, said here so it is not found later: a record or a list a block holds is its own copy, where
Python's is the same object as the world variable it was read from (`<q:set name="r" value="{book}" />` then
`<q:set name="r.page" ...>` changes `book` in Python, not on the machine). No world here does it (every q:set of a
path is on an entity); E3, whose state is Rust's, decides what a record held is. And when two attributes of one
statement both fail, the machine, having evaluated them first, may name the other.

The numbers. On the sessions of the three worlds (30 players, 600 ticks) `World.step` takes 15 to 24 % less with the
rules on the machine (den 953 ms to 726, meadow 476 to 405, Outpost 845 to 693). At the gauge's heaviest, 500 bots
and 1500 beasts on the Rust engine, the rules' share of the tick is 201 ms where it was 209: the expressions were
never the cost there. A profile of that tick says where it is: the world's own functions the brains call,
`nearest()` and the tile and occupancy checks under it (1.9 million `tile_of` calls in 30 ticks, 45 % of the time),
Python's, over Python's state. So E3 is next as planned: the world's state, its index and those functions in Rust,
where the machine's calls to them cost no crossing.
