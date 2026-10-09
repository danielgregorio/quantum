# Declarative multiplayer

> Status: a first slice works (`qg:multiplayer`, `tests/godot/test_godot_multiplayer.py`).
> This page says what it is, why it is this and not something else, what it
> costs, and what is left.

## The idea in one paragraph

A Quantum game is a deterministic simulation: every rule runs in the
physics tick, the only random source is the scene's seed, and the players
reach the game only through input actions. The replay harness proves it in
CI every day: the same tape, the same game. Multiplayer follows from that
without a new concept: **every peer runs the whole game, and a tick runs
when every player's input for it has arrived.** Nothing is synchronised
but the inputs; there is no server state, no interpolation, no prediction,
no "networked node". The game says one line, `<qg:multiplayer players="2" />`,
and names which character is whose with `player=`, which it already did for
two people on one keyboard.

## What the game says

```xml
<qg:multiplayer players="2" delay="3" check-every="60" />
<qg:character id="left" controller="ship" player="1" ... />
<qg:character id="right" controller="ship" player="2" ... />
```

- `players`: how many peers the game waits for before it starts.
- `delay`: ticks between a press and its effect, on every peer alike — the
  input latency that hides the round trip (3 ticks is 50 ms at 60 Hz).
- `check-every`: every so many ticks the peers compare a hash of the whole
  `quantum_state()`; a difference is a desync, reported with the tick and
  fatal — never a silent drift.

Keys are declared for player 1 only (or the defaults): on each machine the
local keys are *that machine's* player, whichever number it was given. A
game with `qg:multiplayer` still runs alone: without `--q-host`/`--q-join`
it is the single-keyboard game it was.

## How it runs

```
godot --path projects/pong/godot -- --q-host=7777            # player 1
godot --path projects/pong/godot -- --q-join=HOST:7777       # player 2
```

The host is player 1; joiners are players 2.. in the order they connect;
the first scene is built on every peer once everyone is there. Then, each
tick, on each peer (`addons/quantum/lockstep.gd`):

1. Sample the local `raw_<action>` actions (the keys are rebound to these
   at start, so a key never reaches the game directly), pack them into a
   bit mask, record it for tick `t + delay` and send it to every peer
   (one reliable RPC of three integers).
2. If every player's mask for tick `t` is known, press and release the
   real actions (`up`, `p2_up`...) through `Input.action_press`, the same
   call the replay harness uses, and let the scene run its tick. If not,
   disable the scene's processing for this frame: the world stands still
   until the late input arrives.
3. Every `check-every` ticks, hash the state and exchange it.

The runtime is ~200 lines of GDScript, and the compiler's part is to
register every player's actions and carry the three numbers in `game.json`.
No controller, prefab or handler knows multiplayer exists.

## Why lockstep and not a server

- **It is free.** Determinism was the design's first principle; lockstep
  is what determinism buys. A server-authoritative design would need every
  prefab to be a networked node, a snapshot format, interpolation — the
  very things a declarative language should not make the author think of.
- **It is testable the way everything else here is.** `replay_peers()`
  runs N headless Godots on localhost under tapes and returns N states;
  the test asserts they are equal, and equal to one Godot replaying all the
  tapes shifted by the delay. Multiplayer correctness is a replay test.
- **It is honest about its limit.** Lockstep is for a handful of players
  on a connection where the round trip fits the delay: two to four people,
  co-op or versus. It is not a shooter with 64 players — nor should the
  first multiplayer in a Laboratory language be.

## What it costs

- Latency: `delay` ticks for everyone, including the local player. 2–5
  ticks is the usual range; a game can raise it for a slow link.
- Stalls: a late packet freezes the world for everyone until it arrives.
  Reliable ENet means it always arrives.
- Determinism across machines: the same Godot binary on the same
  architecture gives the same floats. Across architectures (an x86 host
  and an ARM laptop) `move_and_slide` could in theory round differently;
  the hash check would say so at the first `check-every`. Not observed; not
  proven either.

## What is left

1. **A lobby in the language**: today the host/join choice is a command
   line flag; a `qg:lobby` scene (host, join at an address, wait for
   players, start) would make it a game tag like any other.
2. **Rejoin and spectate**: a peer that leaves ends the game for the rest
   (the others run out their known ticks and stop). Rejoining means
   replaying the input history, which the model allows and the runtime
   does not yet keep.
3. **Rollback** (GGPO-style): predict the remote inputs, run ahead, roll
   back on a miss. Hides the delay entirely; needs state snapshots, which
   `quantum_state()` almost is. The step after lockstep is stable.
4. **Web export**: ENet is not in the browser; WebRTC through Godot's
   `WebRTCMultiplayerPeer` with a signalling service would be.
5. **Three or more players in a game that uses it**: the runtime takes
   any `players`; only Pong (2) exercises it.
