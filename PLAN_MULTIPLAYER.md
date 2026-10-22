# Declarative multiplayer

> Status: lockstep works, started from the game's own lobby (`qg:lobby`, or
> `qg:host`/`qg:join`) or the command line, over ENet or WebSocket
> (`tests/godot/test_godot_multiplayer.py`), for two to as many players as
> the game says, with watchers; rollback for fighting games.
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

1. ~~**A lobby in the language**~~ — done: `qg:host port=`, `qg:join
   address=`, `qg:leave`, `net_status()`/`net_players()`/`net_player()`,
   `qg:multiplayer start=` (the scene the networked game begins in; the
   scenes before it run on each machine alone) and `qg:lobby`, the usual
   menu written by the compiler. Game state set before the start scene is
   each machine's own: the hash check would report a difference.
2. ~~**Rejoin**~~ — done: the host (or the relay) keeps every input of
   the game; when a player leaves the others wait, and the next to join
   takes the seat, gets the inputs so far and runs the game from its start
   16 times faster (the engine runs 16x the ticks with time_scale 16, so a
   tick still steps 1/60 s), checking the hashes the players agreed on.
   Not under rollback. ~~**Spectate**~~ — done: `qg:watch address=`, the
   lobby's **Watch**, `--q-watch=HOST:PORT`. A joiner now says, as it
   connects, whether it plays or watches, and only then gets a seat or none;
   one who watches before the start starts with the players, one who comes
   later gets the inputs so far and catches up. The host (or the relay)
   hands every frame it receives on to those who came late, since Godot's
   own relay can miss one that arrives as they join — which a rejoining
   player could also hit (fixed for both). `tests/godot/test_godot_watch.py`
   has two watchers, one from the start and one three seconds in.
3. ~~**Rollback**~~ — done, for the scenes it can take:
   `<qg:multiplayer rollback="8" />`. Each tick runs at once with the
   others' input guessed (what they last pressed); a snapshot of the state
   is kept before every tick; when an input arrives that was guessed wrong,
   the state goes back to that tick and the ticks since run again inside
   one frame (`addons/quantum/rollback.gd`). The runtime reads input
   through `Q`, one value per tick, so an old tick can be run again with
   its own input. Godot's physics cannot be run again inside a frame, so
   the compiler allows rollback only when every scene the networked game
   reaches holds fighters, timers, menus, the HUD, pictures and a camera —
   nodes that save and load their whole state — and, since 2026-10-21, a
   tilemap (the cells `qg:set-tile` changed) and the scene's tweens (records
   in one `Tweens` node, `tests/godot/test_godot_rollback_tweens.py`). A
   scene change waits until
   the tick that asked for it is certain. Arena uses it, with an input
   delay of 2 ticks; its tests inject 30–120 ms of latency and check both
   peers end where one replay of both tapes ends.
4. ~~**Web export**~~ — done: two browsers meet at `quantum relay`
   (`quantum/runtime/game_relay.py`). A room is the game itself in a
   headless Godot that hosts without a seat (`--q-relay=PORT`): every
   player joins it, and Godot's multiplayer relays each one's inputs to the
   others. The relay process carries WebSocket messages unchanged, and
   with `--cert`/`--key` it is `wss://`, as a page on HTTPS needs. An
   address may be a URL (`wss://relay.example/pong/ROOM`), and a web
   page's `?join=` fills the title's address field (`url_param()`). A
   WebRTC mesh would skip the relay but needs a signalling server anyway.
   `scripts/check-relay-in-browser.py` runs two Chromium pages through a
   relay in CI.
5. ~~**Three or more players in a game that uses it**~~ — done: Bricks
   is for two to four. `<qg:multiplayer players="4" min-players="2" />`:
   the game starts by itself as the fourth joins, or the host starts it
   sooner with those who are there (`qg:start-now`, the lobby's **Start
   now**, or `--q-players=N` on the command line); from then on `players`
   is how many play, what every tick waits for and every hash is compared
   across, and every peer learns it as the game starts. `net_players()`
   says it, so `if="{net_players() >= 3}"` places a third character only
   when there is a third player. Under a relay player 1 asks the relay to
   start. `tests/godot/test_godot_party.py` plays three on three Godots,
   from the game's own menu and from the command line. Not under rollback.
