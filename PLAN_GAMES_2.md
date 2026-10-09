# Games 2 — plan for a complete declarative game engine

> Status: done (2026-10-09, all five phases, on the branch `plan/games-2`).
> Laboratory tier. This is the design the roadmap listed as "Games 2: games
> as a deterministic declarative simulation". Nothing here carries a
> stability promise. The record of what was built and learned is in each
> phase below; the closing notes are at the end.

## The decision

**Keep Godot 4 as the only runtime. Keep the `qg:` language where it is
good. Rebuild the middle — the code generators — from scratch. Retire the
PixiJS backend. Owe nothing to the old games.**

The language is in flux and that is the point of the Laboratory tier: no
tag, attribute or game that exists today is a constraint. The old games
(snake, tic-tac-toe, the Kenney platformer, the example fighter and
adventure) were JavaScript against the PixiJS runtime; they are deleted,
not migrated. Their Kenney CC0 art stays in `assets/kenney/` for the new
games.

Why not rebuild everything: the language layer (`qg:` parser, 1.7k lines of
AST nodes, 84 parser tests) is in good shape and already knows the vocabulary
a platformer needs (`qg:prefab type="enemy" defeated-by="stomp"`,
`qg:enemy` with seven AI kinds, question blocks, checkpoints, a world map,
state that persists between scenes). Throwing that away buys nothing.

Why not keep the generators: they are the part that leaked.

| Problem today | Where |
|---|---|
| Two backends (PixiJS 4.4k lines, Godot 6.1k lines) that drifted: every tag had to be implemented twice, and in practice was implemented in one. **Done first (2026-10-09): the PixiJS backend is deleted; Godot is the only backend.** | `quantum/runtime/game_builder.py` |
| `q:function` bodies are copied through as raw JavaScript / GDScript, line by line. `q:if` and `q:loop` inside a function are silently dropped on Godot. This is the escape hatch every game in `projects/` falls into: the platformer has ~130 lines of JS in 15 functions | `game_engine_2d/src/parser.py:163`, `godot_code_generator.py:4548` |
| Unknown collision actions become a comment and the game builds anyway — against the "nothing without effect" rule | `godot_code_generator.py:4585` |
| Genre rules (stomp, squish, emerge, question block) are hard-coded as special cases in the generator instead of composed from primitives. A third genre means a third pile of special cases | `godot_code_generator.py` (`_write_*_script`, 3k lines) |
| No game uses the Godot backend. Nothing in CI runs Godot, so 259 tests assert generated text, not behaviour | `tests/test_godot_codegen.py` |

Why Godot and not a browser engine or our own: a real engine with an editor,
headless mode for CI (`godot --headless`), exports to web, desktop and mobile
from one project, and GDScript is a small, regular target to generate. The web
still works — Godot's HTML5 export runs in the browser — so retiring PixiJS
loses no platform, only a second implementation. The repository already made
this argument once, about the React Native target: a backend that
"translates on its own" is the opposite of one runtime.

## The architecture: thin compiler, fat runtime

Today the compiler writes a bespoke 4k-line GDScript project per game. Instead:

```
game.q ──parse──> Game AST ──compile──> project/
                                         ├── addons/quantum/      fixed GDScript runtime (versioned, identical in every game)
                                         ├── game.json            the declarative part: scenes, prefabs, tilemaps, HUD, inputs
                                         ├── scripts/*.gd         only the imperative part: q:function bodies, compiled
                                         └── project.godot, export_presets.cfg, assets/
```

1. **`addons/quantum/` — the runtime.** Hand-written GDScript, checked into
   this repository, tested on its own with GUT or Godot's test runner. It
   interprets `game.json`: builds the scene tree, wires collisions, runs the
   kinematic controllers, HUD, timers, spawners, state machines, scene
   transitions, persistence. Genre behaviour lives here as **composable
   components** (`Stompable`, `Collectible`, `Breakable`, `Patrol`, `Chase`,
   `Projectile`, `Spawner`…), not as generator special cases. The compiler
   never emits these; it names them.
2. **`game.json` — the data.** Everything declarative in the `.q` file becomes
   data. Most of a game is this file.
3. **`scripts/*.gd` — compiled logic.** `q:function`, `q:if`, `q:loop`,
   `q:set` and Quantum expressions (`{score + 100}`) compile to GDScript
   through one expression compiler, with the same semantics the Core runtime
   gives them (`quantum/core/expressions.py` is the reference). **Raw text
   inside a `q:function` is a compile error.** When a game needs something the
   language cannot say, the language grows a tag or a built-in; the game does
   not grow a script.

Deterministic by construction (the roadmap's "Games 2" promise): all game
logic runs in `_physics_process` at a fixed 60 Hz; no logic in `_process`;
one seeded RNG per scene (`<qg:scene seed="…">`); own kinematic movement
(CharacterBody2D + tile collision), no rigid-body simulation. Then **replay is
a test**: record inputs per tick, run the game headless for N ticks, assert
state. That is how the games get tested in CI without a screen.

## The language surface at the end

Existing tags stay (with their attributes), plus what the three games force.
Target shape, to be refined by writing the games first:

```xml
<q:application id="…" type="game" engine="godot">       <!-- engine="2d" means godot; pixi is gone -->

  <qg:prefab name="Walker" type="enemy" health="2" defeated-by="stomp" ai="patrol" speed="40" />
  <qg:prefab name="Shroom" type="item" effect="grow" auto-move="true" />
  <qg:prefab name="QBlock" type="block" content="Shroom" hit-from="below" becomes="empty" />

  <qg:character id="player" controller="platformer" hitbox="16x16"
                run-speed="90" jump-height="64" variable-jump="true" coyote-frames="6">
    <qg:state-machine initial="small">
      <qg:state name="small" hitbox="16x16" />
      <qg:state name="big"   hitbox="16x32" />
    </qg:state-machine>
    <qg:on-collision with="enemy" side="top">   <!-- side is new: top/bottom/left/right/any -->
      <qg:destroy target="other" /> <qg:bounce force="200" /> <qg:play sound="stomp" />
      <q:set name="score" value="{score + 100}" />
    </qg:on-collision>
    <qg:on-collision with="enemy" side="any">
      <qg:transition to="small" else="die" /> <qg:invulnerable frames="120" />
    </qg:on-collision>
  </qg:character>

  <qg:scene name="level-1" seed="7" tileset="assets/kenney/tilemap_packed.png" tile="16">
    <qg:tilemap src="levels/1.tmx">                 <!-- Tiled; object layers spawn prefabs -->
      <qg:spawn-layer name="enemies" />
      <qg:spawn-layer name="items" />
    </qg:tilemap>
    <qg:camera follow="player" bounds="tilemap" />
    <qg:hud position="top-left"><qg:counter bind="score" digits="6" /></qg:hud>
    <qg:timer every="30s" action="spawn" prefab="Walker" at="offscreen-right" />
  </qg:scene>
</q:application>
```

Action tags (`qg:destroy`, `qg:bounce`, `qg:play`, `qg:spawn`, `qg:transition`,
`qg:emit`, `qg:goto-scene`, `qg:shake`, `qg:tween`) replace the
`action="destroy-other;emit:x"` strings. Anything else is `q:set`/`q:if`/
`q:loop` on game state with Quantum expressions, as in the rest of the language.

## The three games

Chosen so the engine is not a one-genre engine. Each one is a Laboratory
project under `projects/`, art from Kenney (CC0), neutral names (no
third-party characters, titles or level layouts — see CHANGELOG, the earlier
clean-up for the same reason).

| Game | Genre | What it forces out of the engine |
|---|---|---|
| **Hopper** (platformer, 3 levels + world map) | side-scroller | kinematic controller, tilemaps from Tiled, side-aware collisions, enemies with AI, power-ups and character states, breakable/question blocks, checkpoints, world map, state persisting across scenes, game over screen |
| **Keep** (top-down adventure, ~6 rooms) | top-down | 8-direction movement, room-to-room transitions with the camera snapping, triggers and switches, keys/doors (inventory as state), hearts, melee hitbox, simple enemies, dialogue boxes in the HUD |
| **Drift** (vertical shooter, 3 waves + boss) | arcade | projectiles and pools, spawners on timers and waves, particles, boss state machine with phases, screen shake, lives/continues, high score persisted to disk |

There is no migration: the old games are gone. The smoke test of the new
backend is the first slice of Hopper (phase 1), not an old game.

## Phases

Estimates assume one person full-time; each phase ends green in CI.

### Phase 0 — Ground (3–4 days) — done 2026-10-09

- Godot 4.4.1, pinned in `quantum/runtime/godot_bin.py`; `scripts/godot.py
  install` downloads it into `~/.cache/quantum/godot`; the Laboratory CI job
  installs it (cached) and sets `QUANTUM_GODOT_REQUIRED=1`. `quantum run
  game.q --check` imports the project headless and fails on any script error
  (Godot exits 0 either way, so the output is parsed).
- `quantum/runtime/godot_replay.gd` + `.py`: runs the main scene for N
  physics ticks under an input tape (`Input.action_press`), dumps every
  node's `quantum_state()`. Verified deterministic on
  `tests/godot/fixtures/mover`. Used by every game test after.
- What was learned: the physics tick is the unit; `MainLoop._physics_process`
  runs before the nodes', so the harness controls the count exactly.

### Phase 1 — Runtime addon and new compiler, first slice of Hopper (2 weeks) — done 2026-10-09

- `addons/quantum/`: scene builder from `game.json`, input map, sprites,
  animations, timers, event bus, HUD counters, scene manager, persistence.
- New `quantum/runtime/godot/` package replacing `godot_code_generator.py`
  and `godot_templates.py`: AST → `game.json` + compiled scripts.
- Expression and statement compiler: Quantum expressions → GDScript, `q:set`,
  `q:if`, `q:loop`, `q:function` with parameters and return. Raw text in a
  function is a compile error with the line. Unknown tag or attribute is a
  compile error. Conformance tests: the same expression evaluated by the Core
  evaluator and by Godot gives the same value (table of ~200 cases).
- The first slice of Hopper: one screen, a sprite that walks and jumps on
  a tilemap, a coin to collect, a counter in the HUD. Its replay passes in
  CI.
- Milestone: that slice is a `.q` with zero lines of script, and the old
  generator (`godot_code_generator.py`, `godot_templates.py`) is deleted —
  what it did that the slice needs was rebuilt, the rest waits for a game
  to need it.
- What was built: `quantum/runtime/godot/` (schema, model, expressions,
  statements, compiler) and `addons/quantum/` (game root, scene builder,
  scene base, platformer body, item, tilemap from CSV, HUD). The old
  parser went with the old generator: it rejected every new tag.
- What was learned: in a `.tscn`, `script` is a property line, not a node
  attribute (silently ignored otherwise); `Camera2D.make_current` needs the
  tree, so the scene does it in `_ready`; with gravity applied before the
  move, the take-off speed that peaks at exactly h is
  `g·dt/2 + sqrt((g·dt/2)² + 2·g·h)`; textures load from the image files
  (`Image.load_from_file`), so headless runs need no import step.
- Still open from this phase: the expression conformance table has 21
  cases, not ~200; `q:loop` over a dictionary and slices are not compiled;
  `qg:input` (own keys) does not exist yet — the platformer's actions are
  bound to arrows/WASD/space.

### Phase 2 — Platformer kit and Hopper (3 weeks) — done 2026-10-09

Slices, each one green in CI before the next:

- [x] 2a (2026-10-09): sounds, animations, a patrol enemy, stomp (`side="top"`),
  hurt with `cooldown=`, `qg:bounce`, `qg:respawn`, `qg:on-fall`. Learned:
  two CharacterBody2Ds on the same layer block each other and their areas
  never overlap — things live on layer 2, characters' bodies only see
  layer 1; `is_on_top_of` is "falling, feet above the other's middle".
- [x] 2b (2026-10-09): `qg:state` + `qg:become` (a power-up that grows, a
  hit that shrinks), solid prefabs bumped from below (`side="bottom"`),
  `qg:spawn`, `qg:swap`, `qg:checkpoint`, spikes, a flag, `qg:text`.
  Learned: `move_and_slide` zeroes the velocity on a floor or ceiling
  before the touch is reported, so the side is judged by the pre-move
  velocity; physics refuses new shapes and shape changes during a
  collision callback, so spawn/swap add deferred and a state change
  resizes deferred; a character's sensor is 2 px larger than its body,
  or a solid it rests on is never "touched".
- [x] 2c (2026-10-09): game state (`q:set` in `<q:application>`, the
  autoload `G`), `qg:goto-scene` (deferred to the end of the tick), a
  world map (`controller="map"`, `qg:map-node`, `qg:map-path requires=`
  read against the game's `cleared`), `qg:on-input`, `q:call`, game over,
  three levels. Learned: a held action in the tape is not "just pressed"
  again — a test that presses on the map must release first; a scene
  entered at tick t runs its first tick at t + 2.
- [x] 2d (2026-10-09): `qg:tilemap src="level.tmx"`: tile layers (a
  `collision` property), object layers placing prefabs by class (points,
  rectangles, tile objects). One tileset per map, no flipped tiles, CSV
  only — each refused with a message that says what to change in Tiled.
  Hopper's level 2 is a `.tmx`.

Phase 2 is done. Of the enemy AIs the plan listed, only `patrol` exists:
no game needed the others yet (rule 3). What Hopper did not need and the
language does not have: `qg:input` for own keys, moving platforms,
one-way platforms, a timer, a boss.

- Kinematic `platformer` controller with the existing retro constants
  (variable jump, coyote frames, rising/falling gravity, terminal velocity).
  Tune against a replay suite, not by eye: "from standing, a 12-frame hold
  reaches 64 px" is a test.
- Tilemap from Tiled `.tmx` (tiles, collision layer, object layers → prefabs).
- Side-aware collisions, `qg:character` states that change hitbox, items,
  blocks, checkpoints, enemy AI (`patrol`, `chase`, `hop`, `charge`,
  `emerge`, `fly-patrol`), stomp with squish, world map, game over.
- Hopper: 3 levels, world map, 3 enemy kinds, 2 power-ups.
- Milestone: Hopper playable end to end from a web export; every tag it
  needed exists.

### Phase 3 — Top-down kit and Keep (2 weeks) — done 2026-10-09

What was built: `controller="topdown"` with a swing and `qg:on-hit`;
`qg:exit` with arrival at a named exit of the next scene (the exit is
disarmed until the character leaves it, or it would send it straight
back); `ai="wander"` from the scene's seeded RNG and `ai="chase"`;
`qg:instance if=` (a door opened or a key taken is not placed again) and
`name=`. The camera is simply absent in a room the size of the screen.
What the plan listed and Keep did not need: camera snap/scroll modes,
`qg:trigger`, `qg:dialogue` with paging (a `qg:text` bound to a message
did). Learned: a chasing thing parks on the character, so a swing must
reach the body's own cell too — the swing is `reach` deep and body-plus-
half-reach wide.


- `topdown` controller, 8-direction animation sets, room transitions
  (`qg:door to="room-3" at="east"`), camera snap/scroll modes, triggers
  (`qg:trigger area`), switches, keys as inventory state, melee hitbox as a
  timed child collider, `qg:dialogue` in the HUD with paging.
- Keep: 6 rooms, 2 enemy kinds, 1 locked door, 1 switch puzzle, an ending.

### Phase 4 — Arcade kit and Drift (2 weeks) — done 2026-10-09

What was built: the `ship` controller, `fly`/`sway` AIs with `lifetime`,
health with `qg:damage`/`qg:on-damage`/`qg:on-death`, handlers on
prefabs (compiled into the autoload `P`, with the game state in reach),
states on prefabs (the boss's phases), `qg:spawner` from the scene's
seed, `qg:burst`/`qg:shake`, `saved="true"` state. Not built: object
pooling (Godot copes with a few dozen nodes; a game that needs more will
say so), continues (lives suffice). Learned: `persist=` is a removed
Core attribute the parser refuses, so the game's word is `saved=`.


- Projectiles with pooling, `qg:spawner` with waves, particles, boss as a
  prefab with a `qg:state-machine` driving phases, screen shake, continues,
  high score persisted (`qg:persistent`).
- Drift: 3 waves, 1 boss with 2 phases, high-score table.

### Phase 5 — Document and ship (1 week) — done 2026-10-09

What was done: `docs/targets/games.md` generated from the schema with the
three games whole (`scripts/generate-games-reference.py`, a test keeps it
current), in the site's Build Targets section; the roadmap row, the
Laboratory row of `SUPPORT_TIERS.md`, the CHANGELOG. What was adapted:
the web exports are not built in CI — Godot's export templates are 1.2 GB
per version, so `scripts/export-games.py` builds them for whoever has the
templates installed, and the site does not embed them yet. The three
"build this game" tutorials became the three games on the reference page,
whole and replayed in CI: a tutorial that could rot was not worth more
than a game that cannot.


- (The PixiJS backend was removed before phase 0, with its tests, the
  committed HTML builds and the web pages that framed them. `engine="2d"`
  keeps working and means Godot.)
- `docs/targets/games.md`: the tag reference, generated from the AST nodes the
  way `FEATURE_STATUS.md` is generated, so it cannot rot. Three "build this
  game" tutorials, one per genre, each one tested in CI like the cookbook.
- Web exports of the three games on the site (`docs/public/games/`), built in
  CI.
- CHANGELOG, roadmap row "Games 2" → done, SUPPORT_TIERS updated.

**Total: about 11 weeks.** Phases 3 and 4 can overlap if there are two people;
0–2 are sequential.

## Rules for the whole effort

1. **Write the game before the feature.** Each phase starts by writing the
   game's `.q` as it should read; every tag the compiler rejects is the to-do
   list. Not the other way round.
2. **No escape hatch.** No raw GDScript in `.q`, no `qg:script`, no
   `lang="gdscript"`. If a game truly cannot be expressed, that is a language
   finding; record it in the plan and add the smallest general tag.
3. **Every tag has a replay test.** A tag with no game using it and no test
   is deleted at the end of the phase.
4. **Generated output is never edited** (SUPPORT_TIERS already says so). The
   `projects/*/godot/` directories are build output, in `.gitignore`.
5. **Compile errors, not comments.** Unknown tag, attribute, action or
   prefab name fails the build with file and line.
6. **Determinism is tested.** Same tape, same final state hash, in CI, on
   Linux. (Cross-platform determinism is not promised; we use only integer
   tile math and Godot's fixed physics tick.)

## Risks

| Risk | Mitigation |
|---|---|
| Godot binary in CI (~100 MB download, Godot version drift) | pinned version, cached; one place (`scripts/godot.py`) knows the version |
| GDScript expression semantics ≠ Python-like Quantum semantics (integer division, truthiness, string ops) | the conformance table in Phase 1; the compiler emits helper calls (`Q.div`, `Q.truthy`) where they differ |
| The kinematic controller "feels wrong" and tuning drags on | replay tests pin the numbers first; feel is tuned within the tested envelope |
| Three games is a lot of content | levels are data (Tiled); the plan sizes them small (3 levels, 6 rooms, 3 waves) |
| Playground cannot run games (Pyodide has no Godot) | out of scope; the site embeds the web exports instead |

## Open questions, answered along the way

- `game.json`: kept; it is what the runtime reads and what the tests assert on.
- The games live in `projects/` (today's convention).
- `qg:` stays the prefix.

## Closing notes

What exists now: `quantum/runtime/godot/` (schema, model, expressions,
statements, compiler, tiled: ~1.7k lines of Python), `addons/quantum/` (the
runtime: ~1.4k lines of GDScript in 16 files), 36 tags, three games written
in the tags and nothing else (`projects/hopper`, `keep`, `drift`), 180+
tests in `tests/godot/` of which ~60 replay the games in the real engine,
and a generated reference page. The old engine (two backends, 10k lines,
JavaScript in every game) is gone.

What the plan got right: writing each game before its features — every
tag exists because a game needed it, and the "what Hopper/Keep/Drift did
not need" lists are the tags that do not exist. Replay as the test: every
mechanic is a number a tape reproduces (a 64 px jump, a bat that parks at
x=143.5), and tuning happened against those numbers, not by eye. No
escape hatch: not once did a game need script.

What the plan got wrong: the estimates (eleven weeks of calendar for one
person; the work was done in one long session, because the engine does
the heavy lifting and the compiler is thin); the expression conformance
table (a few dozen cases, not two hundred — the games exercised what they
exercised); the web exports in CI (1.2 GB of templates; `scripts/
export-games.py` for whoever has them); the tutorials (the games on the
reference page, whole and replayed, do that job).

Taken up after the plan closed (2026-10-09): `qg:input` (Hopper's jump
keys), `qg:timer` (Hopper's clock, Drift's warning), one-way ledges and
shuttle lifts (Hopper's level 2), slices in expressions and `q:loop`
over a dictionary, and a conformance test that runs 45 expressions in
Godot against the Core evaluator — which found two real language
faults: an untyped `q:set` was a `String` in GDScript (now `Variant`),
and a state named `name` redefined `Node.name` (such names are refused).

What remains open, for a game that needs it: items (non-moving prefabs)
with handlers of their own, cross-platform determinism (Linux is what
CI replays on), and the web exports on the site (1.2 GB of templates).
