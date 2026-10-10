# The play protocol: a game an agent can play

> Status: phases 1 to 4 are built: the driver (`quantum/runtime/godot_play.gd`),
> its client (`godot_play.py`, `PlaySession`), the tools by session
> (`play_tools.py`), the MCP server (`play_mcp.py`, declared in `.mcp.json`)
> and the console (`quantum play`). In `tests/godot/test_godot_play.py` and
> `test_godot_play_mcp.py`, agents:
> - win the RPG in 16 requests, and again through the MCP tools alone;
> - play Chess with the cursor;
> - leave Keep's first room using only the map and the view;
> - read a fight's events hit by hit;
> - branch a fight from a snapshot and come back;
> - replay a session saved as a tape, as a test.
>
> The rest is the plan: what to build, in what order, and how each step is
> checked. It builds on what the replay harness, the lockstep and the
> rollback already do.

## The problem

Today an agent (Claude, a script, a test) "plays" a Quantum game in one of
two ways, and both are poor:

- **Tapes.** The agent writes every key press with its tick in advance, runs
  the game headless, and reads the state at the end. It is exact and it is
  how the tests work, but the agent plays blind: it plans the whole match
  before it sees anything, and a plan that is one cell off fails at the end.
- **Screenshots.** The agent opens the browser build, presses keys in real
  time, and looks at pictures. It sees, but late, through pixels, with no
  numbers, and the game does not wait for it: a decision takes seconds and
  the game moves 60 ticks a second.

What a player needs is a loop: **see what is happening, decide, act, see
what that did.** This proposal gives the agent that loop, at its own pace,
with the game telling it what is happening in data instead of pictures.

## The idea in one paragraph

A Quantum game is a deterministic simulation whose only inputs are actions
(`left`, `jump`, `select`...), and whose whole state is already reported as
data (`quantum_state()`, which every test reads). So the game can be run by
a driver that **advances it only when told to**, applies the actions it is
given, and answers each step with **what the player would see and what
happened**, as JSON. Time belongs to the agent: the game waits, as a
lockstep peer waits for a slow player. Because the game is deterministic,
the whole session is a tape: it can be replayed, branched ("what if I had
defended?") and saved as a test.

```
agent ──act {"hold": ["right"], "ticks": 16}──▶ driver ──▶ Godot (headless)
agent ◀──{ "tick": 48, "scene": "exploration", "player": {"col": 4, "row": 4},
           "events": ["step 3,4 → 4,4"], ... }──────────── driver
```

## What the game says: nothing

The protocol needs no change to any `.q` file and no tag in the language.
What an agent may do is what a player may do: press the game's actions,
point its cursor. The vocabulary is the game's own: its `qg:input`s and the
defaults. There is no escape hatch: the agent cannot set a variable or move a
node, only play.

## Sessions

A session is one running game. The protocol is a sequence of requests,
each answered once; every answer carries the tick it describes.

| Request | Does | Answers |
|---|---|---|
| `start {game, seed?, scene?}` | compiles and opens the game (optionally at a scene, for testing) | the first observation, the controls, the map |
| `observe {detail?}` | nothing | an observation |
| `act {press?, release?, hold?, tap?, cursor?, ticks}` | applies the actions, runs `ticks` ticks | the observation after, and the events of those ticks |
| `until {act?, condition, max_ticks}` | as `act`, but runs until a condition holds | the observation, the events, which condition ended it |
| `snapshot {}` | marks this point | a snapshot id |
| `restore {id}` | goes back to that point | the observation there |
| `frame {scale?}` | renders the screen | a PNG (only when a picture is really needed) |
| `tape {}` | nothing | the session's inputs as a replay tape |
| `end {}` | closes the game | — |

Actions:

- `hold: ["right"]`: pressed for the whole `act`, released after.
- `tap: ["select"]`: pressed on the first tick, released on the second.
- `press` / `release`: change what stays held across requests, which a
  platformer jump held over several requests needs.
- `cursor: [x, y]`: where the player's `qg:cursor` points, as the replay's
  `cursor_at` does. Menus and Chess's board are played this way.

`until` is what makes the loop cheap. Without it, walking to a door is
twenty requests; with it, it is one request plus a condition:

```json
{"until": {"hold": ["right"]},
 "condition": {"any": ["event:bump", "event:dialogue", "player.col == 11"]},
 "max_ticks": 600}
```

Conditions are a small fixed set, evaluated by the driver, not by the game:
- an event kind;
- a comparison on a path of the observation (`scene`, `player.col`,
  `combat.turn`);
- `idle`: no state changed for N ticks, for "wait until the animation ends".

## Observations

An observation is what a player could know by looking, as data, so that it
is small and exact. It has layers, and `detail` picks how many:

1. **State** (always). What `quantum_state()` already reports:
   - the scene;
   - the scene's and the game's variables (life, potions, score);
   - the characters (position, cell, facing, health, state);
   - the things by tag with positions;
   - `paused`, `talking`, the menus.
2. **Interface** (always). What is on the screen to read and choose:
   - every HUD text as it is shown ("Potions 1");
   - each open menu's buttons, with label, enabled, and which has the focus;
   - the dialogue's speaker and line;
   - the camera's rectangle in world coordinates.
3. **Events** (always, since the last answer). What happened, in order, with
   its tick:
   - scene changes;
   - handlers that ran (`on-collision player×key`), damage and deaths;
   - things spawned and destroyed;
   - dialogue lines shown;
   - menu buttons chosen;
   - sounds;
   - bumps and landings.

   A player feels these; an agent would otherwise have to diff states to
   find them.
4. **Map** (on `start` and on each scene change). The tilemap as a grid of
   what is solid, one-way or empty, with the cell size, and the scene's
   size. An agent plans paths on this, not on pixels.
5. **View** (on request). A text picture of the screen at cell resolution:
   the map's walls, the characters and things by letter, with a legend.
   This is for the agent's spatial sense, the way a person glances at the
   screen:

   ```
   ####################      @ player   O opponent
   #.p.............#.##      k key      p potion
   #.....#####.......##
   #..@..##k........###
   ```

6. **Frame** (only through `frame`). The real picture, for what data does
   not capture: does it look right, is something drawn wrong.

Observations are diffs by default: the first one is whole, later ones carry
what changed (`"changed": {"player.col": 4}`), and `observe {"full": true}`
asks for everything. A typical answer should stay under 2 KB.

## Time

- **Step mode** (the default). The game stands still between requests. An
  `act` runs exactly `ticks` ticks at the fixed 60 Hz, as the replay does,
  headless and faster than real time (thousands of ticks a second).
  Nothing is missed and nothing depends on the agent's speed.
- **Reflexes** (for action games). Some games cannot be played a decision per
  request: Pong's paddle must follow the ball every tick. An agent may hand
  the driver small rules that run inside the step loop, every tick, until
  replaced:

  ```json
  {"reflex": [{"when": "ball.y < left.y - 8", "hold": ["up"]},
              {"when": "ball.y > left.y + 8", "hold": ["down"]}]}
  ```

  A reflex is a list of condition-and-action pairs over the observation's
  paths, in a fixed small grammar evaluated by the driver. It is not code,
  and it sits outside the game: what it presses goes into the tape like any
  input, so a match played with reflexes replays the same. The agent plays
  the strategy; the reflexes hold the paddle.
- **Real time** (later, for the browser). The same protocol against a game
  running at its own speed, for watching an agent play, or for an agent
  playing *with* a person (below).

## Branching, and every session is a test

Because the game is deterministic, a session is fully described by its seed
and its inputs. That gives two features almost for free:

- **Snapshots.** `snapshot` records the tick and the inputs so far. `restore`
  gets back there in one of two ways:
  - a scene made only of nodes that save their state (`q_save`/`q_load`,
    what the rollback already requires) is restored in memory, at once;
  - any other scene is restored by replaying the inputs from the start,
    headless. That takes about a second for a few minutes of play, and is
    exact by the same guarantee the tests rely on.

  So an agent can try "attack" and "defend" from the same point and
  compare.

  As built, every restore is by replay: a fresh game, replayed to the
  snapshot's tick. It works for every game, and costs about a second. The
  restore in memory, for the scenes the rollback can save, is an
  optimization left for when a second is too long.
- **Tapes.** `tape` returns the session's inputs in the replay format.
  Saved next to an expected state, a session is a regression test: "the
  agent won the RPG in 1240 ticks with this tape" goes into
  `tests/godot/`, and the next change that breaks the win breaks the test.

## Transports

One protocol, several ways to reach it, built in this order:

1. **Godot driver + JSON lines.** A `godot_play.gd` main loop, the sibling of
   `godot_replay.gd`. It reads a request from stdin, runs it, and writes the
   answer to stdout, one JSON object per line. It works wherever Godot runs
   headless, CI included.
2. **Python client.** `quantum.runtime.godot_play.PlaySession`: `start`,
   `act`, `until`, `observe`, `snapshot`, `restore`, `frame`, `tape`. Tests
   and scripts use this.
3. **CLI.** `quantum play projects/rpg/rpg.q`, a small console where a
   person types `right 3`, `until talking`, `view`, `snap`, `back 1`.
   It is useful to anyone debugging a game, and it is how a person checks
   what an agent sees.
4. **MCP server.** `quantum play --mcp` exposes the requests as tools:
   - `play_games`, `play_start`, `play_observe`, `play_act`, `play_until`;
   - `play_snapshot`, `play_restore`, `play_frame`, `play_tape`, `play_end`.

   With a `.mcp.json` in the repository, any Claude Code session opened on it
   can play the games directly, the way it calls GitHub's tools now.
5. **Browser bridge** (later). The same requests against a web build through
   Playwright, with the game reporting its observation through
   `JavaScriptBridge`, as `window.quantumScene` already does. This checks
   the exported builds, and it is the real-time mode.

## Playing with people

The lockstep already treats a remote player as nothing more than a source
of inputs for one `player=` number. A play session can be that source. An
agent then becomes player 2 in Pong, Arena, Chess or Towers: a person hosts
from the site or the desktop build, and the agent joins through the
protocol. Nothing in the games changes. This is how the two-player games
get an opponent when no friend is around.

## What it is for

- **Playtesting by an agent.** "Play Hopper to the flag and tell me where
  you died and why." It produces findings like a softlock, a jump that
  cannot be made, a fight that is too easy, or a menu that cannot be left,
  each with the tape that shows it.
- **Exact bug reports.** Every finding comes with its tape, so it
  reproduces.
- **A playtest job.** A scheduled job, not on every pull request, in which
  an agent tries to finish each game. Each game in `projects/games.json`
  gets a `goal` (`"rpg": "win the fight"`, `"hopper": "reach the flag of
  level 1"`), and the job reports reached, not reached or stuck, with
  tapes. A goal reached is kept as a test.
- **Opponents.** Above.
- **Accessibility.** The observation describes the game in words: what is
  on screen, what the menu offers, what was said. That is the ground for a
  screen-reader mode later.

## How it is built: phases, and how each is checked

| Phase | Builds | Done when |
|---|---|---|
| 1. Driver (built) | `godot_play.gd`; `start`/`observe`/`act`/`until`/`end`; state and interface layers; Python client | a test plays the RPG to victory through the client, deciding each step from the last observation, in under 40 requests; another plays Chess (e2-e4, e7-e5) with the cursor |
| 2. Perception (built) | events (one `Q.event()` call at each place the runtime already acts: scene change, handler, spawn, destroy, damage, dialogue, menu choice; it does nothing outside a session); the map; the text view; `frame` | Keep's room 1 is crossed to its exit using only the map and the view; the events of an RPG fight list each hit with its damage |
| 3. Branching (built; restores by replay) | `snapshot`/`restore` (in memory for rollback scenes, by replay otherwise); `tape` | restore-then-replay gives byte-identical state hashes, in both modes; a tape saved from a session passes as a test |
| 4. CLI and MCP (built) | `quantum play` console; `quantum play --mcp`; `.mcp.json` | a Claude Code session on the repository is asked "play the RPG and win" and does it through the tools |
| 5. Reflexes | the reflex grammar, in the step loop | in Pong the agent returns 10 balls in a row; in Drift it clears the first wave |
| 6. Browser and people | the browser bridge; joining a lockstep game as player 2 | the agent plays Pong against a person on the web build |
| 7. Playtest job | `goal`s in `projects/games.json`; a scheduled job with a report | the job runs over every game and writes its report |

Phases 1 to 3 are the core and are worth having alone. 4 is what makes it
usable from a conversation. 5 to 7 build on top.

## Costs, limits, and what it does not do

- **It is not real time for the agent.** In step mode, reaction speed is not
  part of the game: an agent that would lose a twitch fight in real time
  wins it here. That is right for testing and wrong for fairness. Against
  a person (phase 6) the game runs at its own speed, so a reflex is the
  only way to keep up, and the protocol says so.
- **Determinism is the foundation.** Snapshots by replay and tapes as tests
  hold because the game is deterministic on the same build. That is already
  tested every day by the replays, and the lockstep's desync check would
  catch a break.
- **Events cost a call in the runtime.** `Q.event()` is a no-op outside a
  play session (one boolean check), and it is added where the runtime
  already acts, not in the compiled scripts.
- **Hidden information.** The observation is the screen's information,
  not the whole simulation: no random seeds, no future spawns, no other
  player's keys. A playtest of "can it be won" should not cheat. The full
  state stays available for tests, behind `detail: "debug"`.
- **One dependency.** The MCP server needs the `mcp` Python package, as an
  optional extra (`pip install quantum[play]`). The rest needs nothing new.

## Open questions

1. Should the reflex grammar reuse the game language's expression syntax
   (`{ball.y < left.y - 8}`), compiled by the same compiler into a separate
   driver script? It reads naturally for anyone who writes `.q`, but it
   must stay out of the game itself.
2. The playtest job needs an agent and an API key. Should it run on a
   schedule in this repository's CI, or only when someone starts it?
3. Should observations be in English only, or should a game's texts carry
   their translations as the site's pages do?
